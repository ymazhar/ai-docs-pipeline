#!/usr/bin/env python3
"""
Transcribes audio files using whisper.cpp and saves results as plain text in transcript/.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WHISPER_BIN = Path(__file__).parent / "whisper.cpp" / "build" / "bin" / "whisper-cli"
MODELS_DIR = Path(__file__).parent / "whisper.cpp" / "models"
TRANSCRIPT_DIR = Path(__file__).parent / "transcript"

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".mp4", ".mov", ".webm"}


def find_model(name: str = "base") -> Path:
    candidates = list(MODELS_DIR.glob(f"ggml-{name}*.bin"))
    if not candidates:
        sys.exit(
            f"Model '{name}' not found in {MODELS_DIR}.\n"
            f"Download it with:\n"
            f"  cd whisper.cpp && bash models/download-ggml-model.sh {name}"
        )
    return candidates[0]


def convert_to_wav(src: Path) -> Path:
    """Convert audio to 16kHz mono WAV required by whisper.cpp."""
    if src.suffix == ".wav":
        return src
    dst = src.with_suffix(".wav")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed for {src}:\n{result.stderr.decode()}")
    return dst


def transcribe(audio: Path, model: Path, language: str | None) -> str:
    lang = language or "auto"
    # --suppress-nst: drop non-speech tokens ([noise], [music]…) so whisper
    # does not fall into a repetition loop emitting them across silent/noisy spans.
    cmd = [str(WHISPER_BIN), "-m", str(model), "-f", str(audio),
           "--output-txt", "--suppress-nst", "-l", lang]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"whisper-cli failed for {audio}:\n{result.stderr}")

    txt_file = Path(str(audio) + ".txt")
    if txt_file.exists():
        text = txt_file.read_text(encoding="utf-8").strip()
        txt_file.unlink()
        return text
    return result.stdout.strip()


AUDIO_DIR = Path(__file__).parent / "audio"


def slugify(stem: str) -> str:
    """snake_case a filename stem: lowercase, no spaces, no PascalCase.

    Splits camelCase/PascalCase boundaries, then collapses any run of
    non-word characters into a single underscore (Cyrillic letters survive).
    """
    s = re.sub(r"(?<=[a-zа-яёіїєґ0-9])(?=[A-ZА-ЯЁІЇЄҐ])", "_", stem)
    s = s.lower()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "untitled"


def save_transcript(audio: Path, text: str) -> Path:
    try:
        rel = audio.resolve().parent.relative_to(AUDIO_DIR.resolve())
    except ValueError:
        rel = Path()
    out_dir = TRANSCRIPT_DIR / rel
    out_dir.mkdir(parents=True, exist_ok=True)
    # Naming convention: snake_case, no date in filename — the date lives
    # inside the file as a `> Date: YYYY-MM-DD` header so it flows downstream.
    timestamp = datetime.now().strftime("%Y-%m-%d")
    out_path = out_dir / f"{slugify(audio.stem)}.txt"
    out_path.write_text(f"> Date: {timestamp}\n\n{text}", encoding="utf-8")
    return out_path


def collect_audio_files(paths: list[str]) -> list[Path]:
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(f for f in sorted(path.iterdir()) if f.suffix.lower() in AUDIO_EXTENSIONS)
        elif path.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(path)
        else:
            print(f"Skipping (unsupported format): {path}")
    return files


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio into text files")
    parser.add_argument("input", nargs="+", help="Audio file(s) or a folder of audio")
    parser.add_argument("-m", "--model", default="medium", help="Whisper model (base, small, medium, large)")
    parser.add_argument("-l", "--language", default=None, help="Language (uk, en, etc.); auto-detected if omitted")
    args = parser.parse_args()

    if not WHISPER_BIN.exists():
        sys.exit(
            "whisper-cli not found. Build the project:\n"
            "  cd whisper.cpp && cmake -B build && cmake --build build -j --config Release"
        )

    model = find_model(args.model)
    files = collect_audio_files(args.input)

    if not files:
        sys.exit("No audio files found.")

    for audio in files:
        print(f"Transcribing: {audio.name} ...", end=" ", flush=True)
        wav = convert_to_wav(audio)
        text = transcribe(wav, model, args.language)
        if wav != audio:
            wav.unlink()
        out = save_transcript(audio, text)
        print(f"→ {out.relative_to(Path.cwd())}")

    print(f"\nDone. Transcripts saved: {len(files)}")


if __name__ == "__main__":
    main()
