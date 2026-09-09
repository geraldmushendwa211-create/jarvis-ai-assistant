# JARVIS Setup Guide

Step-by-step setup for Windows, Linux, and macOS — from clone to your first
*"make a Roblox rant"*.

## 1. Prerequisites

| Need | Windows | Linux (Debian/Ubuntu) | macOS |
|---|---|---|---|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) (tick **Add to PATH**) | `sudo apt install python3 python3-venv` | `brew install python` |
| tkinter (status window) | Included ✅ | `sudo apt install python3-tk` | Included ✅ |
| Mic + speakers | Any | Any (PulseAudio/PipeWire) | Any |
| Gemini API key | Free at <https://aistudio.google.com/apikey> | Same | Same |

> No system **ffmpeg** needed — `imageio-ffmpeg` ships its own binary.
> No GPU needed — Whisper runs on CPU (`base`, `int8`).

## 2. Install

```bash
git clone https://github.com/geraldmushendwa211-create/jarvis-ai-assistant.git
cd jarvis-ai-assistant

python -m venv .venv
```

Activate the venv **every new terminal**:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- Linux/macOS: `source .venv/bin/activate`

Then:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This pulls ~15 packages. The big ones are `torch` (via `faster-whisper`,
CPU-only, a few hundred MB) and `moviepy`'s video stack — grab a coffee. ☕

### Linux audio playback note

`playsound3` on Linux plays through **GStreamer**. If you hear nothing:

```bash
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly
```

## 3. Configure

```bash
# Linux/macOS:
cp .env.example .env
# Windows (cmd):
copy .env.example .env
```

Open `.env` and paste your key:

```
GEMINI_API_KEY=AIza...your-key...
```

Optional: set `GEMINI_MODEL` to any model your key can access
(default `gemini-3.5-flash`).

> `.env` is git-ignored. **Never commit your key.** If you did by accident,
> revoke it at [Google AI Studio](https://aistudio.google.com/apikey) and mint a new one.

## 4. Calibrate your mic (recommended)

```bash
python voice/calibrate.py
```

Stay quiet 3 seconds, then talk. Note the silent vs. speaking volume numbers,
then set `SILENCE_THRESHOLD` in `voice/listen.py` between them
(default `90`, tuned for the author's mic).

## 5. Add media

| Folder | Put here |
|---|---|
| `workspace/footage/` | 1+ gameplay recordings (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) |
| `workspace/music/` | `background_music.mp3` (optional — videos still render without it) |
| `workspace/sfx/` | Meme sounds for future skills (optional) |

Full details: [`workspace/README.md`](../workspace/README.md).

## 6. Run

```bash
python brain/main.py
```

No mic handy, or just testing? Type instead of speaking:

```bash
python brain/main.py --text              # type messages, still hear replies
python brain/main.py --text --no-voice   # fully silent CLI: type + read
```

You'll see `JARVIS is online`, a small status window pops up, and it starts
listening. Try:

1. *"activate test skill"* — confirms the skill system works
2. *"make captions red"* — confirms the video skill module loaded
3. *"what have you made?"* — confirms the status reporter works
4. *"make a Roblox rant about admin abusers"* — 🎬 the full pipeline
   (takes a few minutes on first run while Whisper downloads `base`)

Say *"quit"* to exit.

## 7. Run the tests

```bash
python -m unittest discover tests
```

No key, mic, or camera needed. Tests for the video pipeline skip gracefully
until `pip install -r requirements.txt` is complete. Manual end-to-end checks
with real files live in `tests/manual/` — edit the paths inside first.

## 8. Obsidian memory (optional)

Every conversation auto-appends to `JarvisMemory/Conversations/YYYY-MM-DD.md`
next to the repo. Open that folder as an Obsidian vault and you get a
searchable diary of everything you asked JARVIS. Nothing to configure —
delete or ignore the folder if you don't want it (it's git-ignored).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | You skipped step 3 — copy `.env.example` → `.env` and paste your key |
| `No module named 'tkinter'` | Install `python3-tk` (Linux) — or ignore it, JARVIS runs headless with a warning |
| `Skipping skill module ... missing dependency` | Run `pip install -r requirements.txt` inside the activated venv |
| Mic hears nothing / never stops | Recalibrate (step 4); check OS mic permission + default input device |
| `Speech recognition service is unavailable` | STT needs internet (Google backend) — check your connection |
| No voice output (Linux) | Install the GStreamer packages from step 2 |
| `No module named 'torch'` / Whisper errors | `pip install faster-whisper` again; needs ~1 GB free disk for model cache |
| Captions burn fails (`ass filter`) | Rare with the bundled ffmpeg — update with `pip install -U imageio-ffmpeg` |
| First video takes very long | Normal: Whisper `base` (~150 MB) downloads once to `~/.cache/huggingface` |
| `requests to ... timed out` (TTS) | edge-tts needs internet — check connection, then retry |
| Status window freezes | It's on a daemon thread; the voice loop keeps working — restart to reset it |

## Updating

```bash
git pull
pip install -r requirements.txt   # picks up any new dependencies
python -m unittest discover tests # sanity check before running
```
