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
  architecture/   # категорія (довільна назва)
    file.mp3
transcript/
  architecture/   # дзеркалить структуру audio/
    file.txt                   # snake_case, дата всередині (> Date:), мова джерела
analysis/
  architecture/   # дзеркалить transcript/
    file.md                    # структурований аналіз, МОВА ДЖЕРЕЛА
docs/
  architecture/   # дзеркалить analysis/
    file.md                    # AI-документація, ЗАВЖДИ англійською
whisper.cpp/      # git submodule — C++ inference engine
transcribe.py     # лише транскрипція (whisper)
pipeline.py       # повний конвеєр (transcribe → analyze → docs)
requirements.txt  # anthropic SDK
```

**Правило мов:** усі файли в `docs/` — англійською. `transcript/` і `analysis/` —
мовою джерела (аудіо).

## Угода про іменування (для нових файлів)

**Нові** файли створюємо за єдиним стилем:

- **`snake_case`** для імен файлів (напр. `partner_onboarding_checklist.md`), без
  PascalCase і пробілів.
- **Без дати в імені** — дату вказуємо всередині документа в заголовку
  (`> Date: YYYY-MM-DD`). Виняток — точкові артефакти-зрізи (review/snapshot на
  конкретну дату), де дата в імені доречна.
- Файл кладемо у відповідну підтеку за темою; нову тему заводимо лише за потреби.

Конвеєр (`pipeline.py`) дотримується цієї угоди автоматично: транскрипти, аналіз і
доки отримують імена в `snake_case` без дати, дата вписується рядком `> Date:`
всередині кожного файлу й переноситься між етапами. Індекс бази знань
(`docs/README.md`) теж генерується автоматично — вручну його не редагуємо.

## Setup Status

- **whisper.cpp** — зібрано (`whisper.cpp/build/bin/whisper-cli`)
- **Модель** — `ggml-medium.bin` завантажено (`whisper.cpp/models/`)
- **ffmpeg** — потрібен для не-WAV файлів: `brew install ffmpeg`
- **Python deps** — `anthropic` встановлено у `.venv/` (`pip install -r requirements.txt`)
- **API key** — для етапів analyze/docs потрібен `ANTHROPIC_API_KEY`

## One-time Setup (для нової машини)

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
cp .env.local.example .env.local      # потім вписати ключ у .env.local
```
`pipeline.py` автоматично читає `.env.local` (і `.env`) з кореня проєкту;
обидва в `.gitignore`. Альтернативно — `export ANTHROPIC_API_KEY=...` (реальна
змінна середовища має пріоритет над файлом).

## Usage

**Full pipeline (audio → transcript → analysis → docs):**
```bash
./.venv/bin/python pipeline.py audio/                 # все аудіо, всі етапи
./.venv/bin/python pipeline.py audio/meeting.m4a      # один файл
./.venv/bin/python pipeline.py --from analyze         # перезапустити з наявних транскриптів
./.venv/bin/python pipeline.py --from docs --force    # перегенерувати лише доки
./.venv/bin/python pipeline.py audio/ --to analyze    # зупинитись після аналізу
```

**Лише транскрипція (без Claude):**
```bash
python3 transcribe.py audio/ -m medium -l ru
```

Кожен етап ідемпотентний: наявний вихідний файл пропускається (поки немає `--force`).

## Architecture

**transcribe.py** — лише whisper:
- Accepts files or directories; filters by known audio extensions.
- Converts non-WAV files to 16kHz mono WAV via `ffmpeg`, then deletes the temp file.
- Calls `whisper.cpp/build/bin/whisper-cli`; parses the `.txt` sidecar it writes.
- Writes `transcript/<cat>/YYYY-MM-DD_<stem>.txt`, дзеркалить `audio/`.

**pipeline.py** — оркеструє 3 етапи, перевикористовує `transcribe.py`:
- Етапи: `transcribe` → `analyze` → `docs`; межі задаються `--from` / `--to`.
- `analyze` / `docs` викликають Claude (`claude-sonnet-4-6`, adaptive thinking, стрімінг).
- Аналіз — мовою джерела; доки — англійською (системні промпти в `pipeline.py`).
- Шляхи дзеркаляться: `transcript/` → `analysis/` → `docs/` зі збереженням категорії та імені.

## Models

| Model  | Size  | Speed | Notes                        |
|--------|-------|-------|------------------------------|
| base   | 142MB | fast  | good for clear recordings    |
| small  | 466MB | med   | better accuracy              |
| medium | 1.5GB | slow  | recommended for mixed-lang   |
| large  | 3GB   | slow  | best quality                 |
