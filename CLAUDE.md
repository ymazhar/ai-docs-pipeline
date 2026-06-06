# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Knowledge pipeline: audio → transcript → analysis → AI-facing docs.

```
audio → whisper.cpp → transcript/ → [Claude] → analysis/ → [Claude] → docs/
```

## Project Structure

```
audio/
  architecture/   # category (arbitrary name)
    file.mp3
transcript/
  architecture/   # mirrors audio/ structure
    file.txt                   # snake_case, date inside (> Date:), source language
analysis/
  architecture/   # mirrors transcript/
    file.md                    # structured analysis, SOURCE LANGUAGE
docs/
  architecture/   # mirrors analysis/
    file.md                    # AI documentation, ALWAYS in English
whisper.cpp/      # git submodule — C++ inference engine
transcribe.py     # transcription only (whisper)
pipeline.py       # full pipeline (transcribe → analyze → docs)
requirements.txt  # anthropic SDK
```

**Language rule:** all files in `docs/` are in English. `transcript/` and `analysis/`
are in the source language (audio).

## Naming Convention (for new files)

Create **new** files following a single style:

- **`snake_case`** for file names (e.g. `partner_onboarding_checklist.md`), no
  PascalCase and no spaces.
- **No date in the name** — put the date inside the document in the header
  (`> Date: YYYY-MM-DD`). Exception — point-in-time snapshot artifacts
  (review/snapshot for a specific date), where a date in the name is appropriate.
- Place the file in the matching subfolder by topic; create a new topic only when
  needed.

The pipeline (`pipeline.py`) follows this convention automatically: transcripts,
analysis, and docs get `snake_case` names without a date, the date is written as a
`> Date:` line inside each file and carried between stages. The knowledge base index
(`docs/README.md`) is also generated automatically — do not edit it by hand.

## Setup Status

- **whisper.cpp** — built (`whisper.cpp/build/bin/whisper-cli`)
- **Model** — `ggml-medium.bin` downloaded (`whisper.cpp/models/`)
- **ffmpeg** — required for non-WAV files: `brew install ffmpeg`
- **Python deps** — `anthropic` installed in `.venv/` (`pip install -r requirements.txt`)
- **API key** — `ANTHROPIC_API_KEY` is required for the analyze/docs stages

## One-time Setup (for a new machine)

**1. Build whisper.cpp:**
```bash
cd whisper.cpp
cmake -B build && cmake --build build -j --config Release
```

**2. Download a model:**
```bash
cd whisper.cpp
bash models/download-ggml-model.sh medium
```

**3. Install ffmpeg:**
```bash
brew install ffmpeg
```

**4. Python deps + API key:**
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.local.example .env.local      # then put the key into .env.local
```
`pipeline.py` automatically reads `.env.local` (and `.env`) from the project root;
both are in `.gitignore`. Alternatively — `export ANTHROPIC_API_KEY=...` (a real
environment variable takes precedence over the file).

## Usage

**Full pipeline (audio → transcript → analysis → docs):**
```bash
./.venv/bin/python pipeline.py audio/                 # all audio, all stages
./.venv/bin/python pipeline.py audio/meeting.m4a      # a single file
./.venv/bin/python pipeline.py --from analyze         # restart from existing transcripts
./.venv/bin/python pipeline.py --from docs --force    # regenerate docs only
./.venv/bin/python pipeline.py audio/ --to analyze    # stop after analysis
```

**Transcription only (without Claude):**
```bash
python3 transcribe.py audio/ -m medium -l ru
```

Each stage is idempotent: an existing output file is skipped (unless `--force`).

## Architecture

**transcribe.py** — whisper only:
- Accepts files or directories; filters by known audio extensions.
- Converts non-WAV files to 16kHz mono WAV via `ffmpeg`, then deletes the temp file.
- Calls `whisper.cpp/build/bin/whisper-cli`; parses the `.txt` sidecar it writes.
- Writes `transcript/<cat>/YYYY-MM-DD_<stem>.txt`, mirroring `audio/`.

**pipeline.py** — orchestrates 3 stages, reuses `transcribe.py`:
- Stages: `transcribe` → `analyze` → `docs`; boundaries set via `--from` / `--to`.
- `analyze` / `docs` call Claude (`claude-sonnet-4-6`, adaptive thinking, streaming).
- Analysis — in the source language; docs — in English (system prompts in `pipeline.py`).
- Paths are mirrored: `transcript/` → `analysis/` → `docs/` preserving category and name.

## Models

| Model  | Size  | Speed | Notes                        |
|--------|-------|-------|------------------------------|
| base   | 142MB | fast  | good for clear recordings    |
| small  | 466MB | med   | better accuracy              |
| medium | 1.5GB | slow  | recommended for mixed-lang   |
| large  | 3GB   | slow  | best quality                 |