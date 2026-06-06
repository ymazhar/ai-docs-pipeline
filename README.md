# ai-docs-pipeline — turn audio recordings into AI-ready documentation

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![whisper.cpp](https://img.shields.io/badge/transcription-whisper.cpp-orange.svg)](https://github.com/ggml-org/whisper.cpp)
[![Claude API](https://img.shields.io/badge/analysis-Claude-8A2BE2.svg)](https://www.anthropic.com/)
[![Stars](https://img.shields.io/github/stars/ymazhar/ai-docs-pipeline?style=social)](https://github.com/ymazhar/ai-docs-pipeline/stargazers)

**A local-first pipeline that converts spoken audio — meeting recordings, voice
memos, interviews, lectures — into clean, structured Markdown documentation for
your AI knowledge base.** Speech is transcribed **offline** with
[whisper.cpp](https://github.com/ggml-org/whisper.cpp); the
[Claude API](https://www.anthropic.com/) then turns each transcript into a
structured analysis and a distilled, English-language doc.

```
audio → whisper.cpp → transcript/ → [Claude] → analysis/ → [Claude] → docs/
```

- **transcript/** — raw speech-to-text transcription (source language)
- **analysis/** — structured analysis of the conversation (source language)
- **docs/** — distilled, reusable AI-facing documentation (always English)

> The `transcript/`, `analysis/`, and `docs/` directories are **gitignored** — the
> pipeline writes them locally and they are yours to keep. This repo ships only the
> tooling.

## Why use this?

If you think out loud, run a lot of meetings, or record voice notes, the knowledge
lives in audio files nobody ever revisits. This tool gives you a repeatable way to
**convert speech into searchable, version-controlled Markdown** that both humans and
LLMs can read — without uploading your audio anywhere. Transcription is fully offline
on your machine (macOS/Linux); only the de-identified text is sent to Claude for the
analysis and documentation stages.

## Use cases

- **Meeting notes** — turn Zoom / Google Meet / in-person recordings into clean docs.
- **Voice-to-docs** — dictate ideas and get structured Markdown back.
- **AI knowledge base** — build a folder of English docs your agents and RAG can index.
- **Interviews & user research** — transcribe and summarize sessions into findings.
- **Lectures & talks** — convert recordings into study notes or reference material.

## Quick start

```bash
git clone --recurse-submodules https://github.com/ymazhar/ai-docs-pipeline
cd ai-docs-pipeline

# 1. Build whisper.cpp + download a model
cd whisper.cpp && cmake -B build && cmake --build build -j --config Release
bash models/download-ggml-model.sh medium && cd ..

# 2. ffmpeg (for non-WAV input)
brew install ffmpeg

# 3. Python deps + API key
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.local.example .env.local      # then add your ANTHROPIC_API_KEY

# 4. Create the pipeline folders, then drop audio into audio/<category>/
./.venv/bin/python pipeline.py --init   # creates audio/ transcript/ analysis/ docs/

# 5. Run the full pipeline
./.venv/bin/python pipeline.py audio/
```

Full setup, usage, options, and the naming convention are documented in
[`CLAUDE.md`](CLAUDE.md).

## How it works

The pipeline runs three idempotent stages — each output file is skipped if it already
exists (unless `--force`):

1. **Transcribe** — `whisper.cpp` converts audio (any `ffmpeg`-readable format) into a
   text transcript, fully offline.
2. **Analyze** — Claude reads the transcript and produces a structured analysis in the
   **source language**.
3. **Docs** — Claude distills the analysis into reusable documentation, **always in
   English**.

You can start or stop at any stage with `--from` / `--to`, e.g. regenerate only the
docs from existing analysis.

## Tech stack

- **[whisper.cpp](https://github.com/ggml-org/whisper.cpp)** — fast, offline,
  on-device speech recognition (no audio leaves your machine).
- **[Claude API](https://www.anthropic.com/)** (`claude-sonnet-4-6`) — analysis and
  documentation generation with streaming.
- **Python 3.9+** — the orchestration in `pipeline.py` / `transcribe.py`.
- **ffmpeg** — audio format conversion.

## FAQ

**Does my audio get uploaded anywhere?**
No. Transcription is 100% local via whisper.cpp. Only the resulting text is sent to
the Claude API for the analysis and docs stages.

**What audio formats are supported?**
Anything `ffmpeg` can read — `.mp3`, `.m4a`, `.wav`, `.flac`, and more. Non-WAV files
are converted to 16 kHz mono WAV automatically.

**Do I need an Anthropic API key?**
Only for the analysis and docs stages. You can run transcription alone with
`transcribe.py` and no API key.

**Which whisper model should I use?**
`medium` is the recommended default for mixed-language audio. Smaller models (`base`,
`small`) are faster; `large` is the most accurate. See the model table in
[`CLAUDE.md`](CLAUDE.md).

**Does it work on Windows?**
It's built and tested on macOS/Linux. whisper.cpp itself supports Windows, but the
helper scripts assume a Unix shell.

## License

[MIT](LICENSE)
</content>
</invoke>
