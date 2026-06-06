# ai-docs-pipeline

Turn spoken audio into AI-facing documentation, fully locally:

```
audio → whisper.cpp → transcript/ → [Claude] → analysis/ → [Claude] → docs/
```

- **transcript/** — raw transcription (source language)
- **analysis/** — structured analysis (source language)
- **docs/** — distilled, reusable documentation (always English)

Transcription runs offline via [whisper.cpp](https://github.com/ggml-org/whisper.cpp);
the analysis and docs stages call the Claude API.

> The `transcript/`, `analysis/`, and `docs/` directories are **gitignored** — the
> pipeline writes them locally and they are yours to keep. This repo ships only the
> tooling.

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

# 4. Run the full pipeline
./.venv/bin/python pipeline.py audio/
```

Full setup, usage, options, and the naming convention are documented in
[`CLAUDE.md`](CLAUDE.md).

## License

MIT
