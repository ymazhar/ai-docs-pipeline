#!/usr/bin/env python3
"""
End-to-end knowledge pipeline:

    audio/  ──(whisper.cpp)──▶  transcript/  ──(Claude)──▶  analysis/  ──(Claude)──▶  docs/

Stage 1 (transcribe) reuses transcribe.py.
Stage 2 (analyze)   produces a structured analysis in the SOURCE language.
Stage 3 (docs)      distills the core idea into English AI-facing documentation.

Each stage is idempotent: an existing output is skipped unless --force.

Examples:
    python3 pipeline.py audio/                      # full chain for every audio file
    python3 pipeline.py audio/meeting.m4a           # single file, all stages
    python3 pipeline.py --from analyze              # re-analyze + re-doc existing transcripts
    python3 pipeline.py --from docs --force         # regenerate docs from existing analyses
    python3 pipeline.py audio/ --to analyze         # stop after the analysis stage
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit(
        "The 'anthropic' package is not installed. Install it:\n"
        "  pip install -r requirements.txt   (or: pip install anthropic)"
    )

from transcribe import (
    AUDIO_DIR,
    AUDIO_EXTENSIONS,
    TRANSCRIPT_DIR,
    convert_to_wav,
    find_model,
    save_transcript,
    slugify,
    transcribe,
    WHISPER_BIN,
)

ROOT = Path(__file__).parent
ANALYSIS_DIR = ROOT / "analysis"
DOCS_DIR = ROOT / "docs"

# Base directories the pipeline reads from / writes to. AUDIO_DIR and
# TRANSCRIPT_DIR come from transcribe.py; the other two are defined above.
BASE_DIRS = [AUDIO_DIR, TRANSCRIPT_DIR, ANALYSIS_DIR, DOCS_DIR]

# Speed/cost balance; adaptive thinking + high effort for quality.
CLAUDE_MODEL = "claude-sonnet-4-6"

STAGES = ["transcribe", "analyze", "docs"]


def load_env_file() -> None:
    """Load KEY=VALUE pairs from .env.local / .env into os.environ.

    Real environment variables take precedence (we never overwrite them).
    """
    for name in (".env.local", ".env"):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            os.environ.setdefault(key, value)

def ensure_base_dirs() -> list[Path]:
    """Create the pipeline's base folders if missing; return the ones created."""
    created: list[Path] = []
    for d in BASE_DIRS:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


ANALYSIS_SYSTEM = """\
You are an expert analyst. The user message is a raw transcript of a spoken talk \
or lecture, auto-transcribed and possibly containing recognition errors.

Produce a thorough, well-structured analysis covering:
- the central thesis,
- the key ideas and how they connect,
- the talk's structure,
- important examples and what they illustrate,
- practical takeaways, and any exercises or tasks the speaker assigns,
- notable nuances, caveats, or contradictions.

Silently correct obvious transcription errors in your understanding. \
Write the analysis in THE SAME LANGUAGE as the transcript. Use clear Markdown \
with headings. Do not add meta commentary about being an AI or about the task."""

DOCS_SYSTEM = """\
You are a technical writer building an "ai-docs" knowledge base — documentation \
meant to be consulted by AI agents when they perform related tasks.

The user message is an analysis of a talk. Extract the core, reusable idea(s) and \
turn them into clear, actionable documentation: principles, guidelines, checklists, \
and concrete patterns an AI can apply directly. Omit narrative, biographical, or \
time-bound filler — keep only durable, transferable knowledge.

Write in ENGLISH regardless of the input language. Use structured Markdown with a \
descriptive H1 title. Be concise and practical. Do not add meta commentary."""


DATE_RE = re.compile(r"Date:\s*(\d{4}-\d{2}-\d{2})")


def extract_date(text: str) -> str:
    """Pull the `> Date: YYYY-MM-DD` header from a source file; today if absent."""
    match = DATE_RE.search(text)
    return match.group(1) if match else date.today().isoformat()


def with_date_header(markdown: str, day: str) -> str:
    """Insert `> Date: YYYY-MM-DD` right after the H1 title (or at the top)."""
    header = f"> Date: {day}"
    lines = markdown.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i + 1:i + 1] = ["", header]
            return "\n".join(lines)
    return f"{header}\n\n{markdown}"


def mirror_path(src: Path, base_in: Path, base_out: Path, suffix: str) -> Path:
    """Map a file under base_in to the equivalent path under base_out."""
    try:
        rel = src.resolve().relative_to(base_in.resolve())
    except ValueError:
        rel = Path(src.name)
    return (base_out / rel).with_suffix(suffix)


def collect_files(paths: list[str], default_dir: Path, exts: set[str]) -> list[Path]:
    """Gather files with the given extensions from paths (or default_dir)."""
    roots = [Path(p) for p in paths] if paths else [default_dir]
    files: list[Path] = []
    for path in roots:
        if not path.exists():
            sys.exit(
                f"Not found: {path}\n"
                f"Hint: files live in category subfolders, e.g. "
                f"{default_dir.name}/<category>/<file>."
            )
        if path.is_dir():
            matched = sorted(f for f in path.rglob("*") if f.suffix.lower() in exts)
            if not matched:
                print(f"Empty (no supported files): {path}")
            files.extend(matched)
        elif path.suffix.lower() in exts:
            files.append(path)
        else:
            print(f"Skipping (unsupported format): {path}")
    return files


def call_claude(client: "anthropic.Anthropic", system: str, text: str) -> str:
    """Single Claude call; streamed to avoid timeouts on long transcripts."""
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=system,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": text}],
    ) as stream:
        message = stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text").strip()


# ── Stage 1: transcribe ─────────────────────────────────────────────────────


def stage_transcribe(inputs: list[str], whisper_model: str, language: str | None,
                     force: bool) -> list[Path]:
    if not WHISPER_BIN.exists():
        sys.exit(
            "whisper-cli not found. Build the project:\n"
            "  cd whisper.cpp && cmake -B build && cmake --build build -j --config Release"
        )
    model = find_model(whisper_model)
    audio_files = collect_files(inputs, AUDIO_DIR, AUDIO_EXTENSIONS)
    if not audio_files:
        sys.exit("No audio files found.")

    outputs: list[Path] = []
    for audio in audio_files:
        out = mirror_path(audio, AUDIO_DIR, TRANSCRIPT_DIR, ".txt")
        # Naming convention: snake_case, no date in filename (save_transcript matches).
        out = out.with_name(f"{slugify(audio.stem)}.txt")
        if not force and out.exists():
            print(f"⏭  Transcript exists: {out.relative_to(ROOT)}")
            outputs.append(out)
            continue
        print(f"🎙  Transcribing: {audio.name} ...", end=" ", flush=True)
        wav = convert_to_wav(audio)
        text = transcribe(wav, model, language)
        if wav != audio:
            wav.unlink()
        saved = save_transcript(audio, text)
        print(f"→ {saved.relative_to(ROOT)}")
        outputs.append(saved)
    return outputs


# ── Stage 2: analyze ────────────────────────────────────────────────────────


def stage_analyze(client: "anthropic.Anthropic", transcripts: list[Path],
                  force: bool) -> list[Path]:
    outputs: list[Path] = []
    for tpath in transcripts:
        out = mirror_path(tpath, TRANSCRIPT_DIR, ANALYSIS_DIR, ".md")
        if out.exists() and not force:
            print(f"⏭  Analysis exists: {out.relative_to(ROOT)}")
            outputs.append(out)
            continue
        print(f"🧠  Analyzing: {tpath.name} ...", end=" ", flush=True)
        text = tpath.read_text(encoding="utf-8")
        analysis = call_claude(client, ANALYSIS_SYSTEM, text)
        analysis = with_date_header(analysis, extract_date(text))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(analysis + "\n", encoding="utf-8")
        print(f"→ {out.relative_to(ROOT)}")
        outputs.append(out)
    return outputs


# ── Stage 3: docs ───────────────────────────────────────────────────────────


def stage_docs(client: "anthropic.Anthropic", analyses: list[Path],
               force: bool) -> list[Path]:
    outputs: list[Path] = []
    for apath in analyses:
        out = mirror_path(apath, ANALYSIS_DIR, DOCS_DIR, ".md")
        if out.exists() and not force:
            print(f"⏭  Doc exists: {out.relative_to(ROOT)}")
            outputs.append(out)
            continue
        print(f"📄  Generating doc: {apath.name} ...", end=" ", flush=True)
        text = apath.read_text(encoding="utf-8")
        doc = call_claude(client, DOCS_SYSTEM, text)
        doc = with_date_header(doc, extract_date(text))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc + "\n", encoding="utf-8")
        print(f"→ {out.relative_to(ROOT)}")
        outputs.append(out)
    return outputs


# ── Knowledge-base index ─────────────────────────────────────────────────────


H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def doc_title(path: Path) -> str:
    """First H1 of a markdown file, falling back to the filename stem."""
    match = H1_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else path.stem


def build_docs_index() -> Path:
    """Regenerate docs/README.md: an auto-built catalog of docs/<category>/*.md.

    Hand-editing is pointless — this is overwritten on every pipeline run.
    """
    lines = ["# Knowledge base", "",
             "<!-- Auto-generated by pipeline.py — do not edit by hand. -->", ""]
    categories = sorted(p for p in DOCS_DIR.iterdir() if p.is_dir())
    has_docs = False
    for cat in categories:
        docs = sorted(cat.glob("*.md"))
        if not docs:
            continue
        has_docs = True
        lines.append(f"## {cat.name}")
        lines.append("")
        for doc in docs:
            lines.append(f"- [{doc_title(doc)}]({cat.name}/{doc.name})")
        lines.append("")
    if not has_docs:
        lines.append("_No documents yet._")
        lines.append("")
    index = DOCS_DIR / "README.md"
    index.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return index


def main() -> None:
    load_env_file()
    parser = argparse.ArgumentParser(
        description="Pipeline: audio → transcript → analysis → AI documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="*",
                        help="Files/folders for the starting stage (default: the stage's folder)")
    parser.add_argument("--init", action="store_true",
                        help="Create the pipeline's base folders (audio/ transcript/ "
                             "analysis/ docs/) and exit")
    parser.add_argument("--from", dest="start", choices=STAGES, default="transcribe",
                        help="Stage to start from (default: transcribe)")
    parser.add_argument("--to", dest="stop", choices=STAGES, default="docs",
                        help="Stage to stop at (default: docs)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if the output file already exists")
    parser.add_argument("-m", "--model", default="medium",
                        help="Whisper model (base, small, medium, large)")
    parser.add_argument("-l", "--language", default=None,
                        help="Audio language for whisper (uk, ru, en…); auto if omitted")
    args = parser.parse_args()

    if args.init:
        created = ensure_base_dirs()
        if created:
            for d in created:
                print(f"📁 Created: {d.relative_to(ROOT)}/")
        else:
            print("All base folders already exist.")
        return

    # Make sure the base folders exist so the pipeline never trips over a
    # missing audio/, transcript/, analysis/ or docs/ on a fresh checkout.
    ensure_base_dirs()

    start_i, stop_i = STAGES.index(args.start), STAGES.index(args.stop)
    if start_i > stop_i:
        sys.exit(f"--from {args.start} comes after --to {args.stop}")

    needs_claude = stop_i >= STAGES.index("analyze")
    client = None
    if needs_claude:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            sys.exit(
                "ANTHROPIC_API_KEY is not set. Set the key before running, e.g.:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-..."
            )
        client = anthropic.Anthropic()

    # Resolve the working set as we move through the stages.
    transcripts: list[Path] = []
    analyses: list[Path] = []

    if start_i == STAGES.index("transcribe"):
        transcripts = stage_transcribe(args.input, args.model, args.language, args.force)
    elif start_i == STAGES.index("analyze"):
        transcripts = collect_files(args.input, TRANSCRIPT_DIR, {".txt"})
    elif start_i == STAGES.index("docs"):
        analyses = collect_files(args.input, ANALYSIS_DIR, {".md"})

    if start_i <= STAGES.index("analyze") <= stop_i:
        analyses = stage_analyze(client, transcripts, args.force)

    if STAGES.index("docs") <= stop_i and start_i <= STAGES.index("docs"):
        if not analyses and start_i == STAGES.index("docs"):
            analyses = collect_files(args.input, ANALYSIS_DIR, {".md"})
        stage_docs(client, analyses, args.force)

    if DOCS_DIR.exists():
        index = build_docs_index()
        print(f"🗂  Index updated: {index.relative_to(ROOT)}")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
