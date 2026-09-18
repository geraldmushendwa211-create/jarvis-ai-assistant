# J.A.R.V.I.S. — AI Assistant & Roblox Shorts Factory

A voice-controlled AI assistant (think Iron Man's JARVIS, loyal to *Sir Gerald*)
with a butler personality, reminders, a permission system — and a killer feature:
it **produces captioned, vertical Roblox rant videos end-to-end from one voice command**.

Say *"make a Roblox rant about admin abusers"* and JARVIS writes the script with
Gemini, records a British neural voiceover, trims the dead air, cuts it over your
gameplay footage in 1080×1920, burns in word-by-word captions, and mixes
background music underneath. Final render lands in `workspace/output/`.

## ✨ Features

| Area | What it does |
|---|---|
| 🎙️ Voice loop | Mic → speech-to-text → Gemini (streaming) → neural TTS that starts speaking before the full reply arrives |
| 🎬 Roblox Shorts pipeline | Script → voiceover → silence trim → vertical assembly → styled captions → auto-leveled music |
| 💡 Idea brainstorming | *"give me 5 Roblox video ideas about tycoons"* — saved to `workspace/scripts/` |
| 📊 Project status | *"what have you made?"* — instant report of videos, scripts, and ideas |
| ⏰ Reminders | *"remind me to check the oven in 20 minutes"* — background checker speaks up on time |
| 🔐 Permissions | Skills declare `safe` / `approval_required` / `restricted`; risky actions need your **yes + code word** |
| 🧠 Memory | Conversation history (trimmed for speed) + every exchange logged to an Obsidian vault |
| 🪟 Status window | Tiny live UI showing `IDLE / LISTENING / THINKING / EXECUTING / SUCCESS / ERROR` |

## 🚀 Quickstart

**Prerequisites:** Python 3.10+, a microphone, and a free
[Gemini API key](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/geraldmushendwa211-create/jarvis-ai-assistant.git
cd jarvis-ai-assistant

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then paste your GEMINI_API_KEY into .env
```

JARVIS treats external content as untrusted and keeps risky actions behind
explicit approval prompts. Keep `.env`, API keys, tokens, and client secrets
private, and use an OS account lock and disk encryption as the outer security
layer.

Drop a gameplay recording into `workspace/footage/` (any `.mp4/.mov/.mkv/.avi`),
optionally put `background_music.mp3` in `workspace/music/`, then:

```bash
python brain/main.py
# No mic?  python brain/main.py --text --no-voice   (type + read, fully silent)
# Flags:    python brain/main.py --help
```

For a native Windows desktop build, use PowerShell from the repository root:

```powershell
.\build_windows.ps1
```

Launch `dist\Jarvis\Jarvis.exe`. The native Tkinter status window is enabled
by default; the browser dashboard is disabled unless you start with `--web` or
set `JARVIS_WEB_UI=1`. Copy `.env` beside the executable, and never place API
keys, tokens, client secrets, or personal data into the packaged application.

> 🧭 **New here?** Follow the step-by-step **[Setup Guide](docs/SETUP.md)** —
> it covers Linux/macOS extras (tkinter, GStreamer), mic calibration, Obsidian,
> and troubleshooting.

## 🎤 Things to say

| Say | What happens |
|---|---|
| *"make a Roblox rant about pay-to-win"* | Full Short pipeline → `workspace/output/output_final_*.mp4` |
| *"make a rant about campers, use parkour.mp4"* | Same, but with a specific footage clip |
| *"make a Minecraft short about diamonds"* | Universal skill: any niche (minecraft, gym, horror, tech…), tracked as a project ticket |
| *"make a 10-minute documentary about black holes"* | Long-form pipeline: 16:9 assembly + thumbnail + SEO pack + QC gate |
| *"upload my latest video to youtube"* | Approval-gated upload (private by default) + URL stamped on the project ticket |
| *"what's trending in tech"* / *"research black holes"* / *"plan a video about…"* | Strategy skill: live trends, fact briefs, full video plans → `workspace/scripts/plan_*.md` |
| *"give me 5 video ideas about pets"* | Brainstorms hooks → `workspace/scripts/ideas_*.txt` |
| *"make captions red"* | Caption color for future renders (gold/white/red/cyan/green/pink/purple) |
| *"what have you made?"* | Report of finished videos, scripts, ideas |
| *"execute business idea for custom furniture"* | Create a universal business execution project; safe local tasks are queued, risky tasks wait for approval, and financial tasks are blocked |
| *"show my business tasks"* / *"approve task 2"* | Review or update the latest business task queue; approval never performs an external action |
| *"check system"* / *"run diagnostics"* | Read-only check of Python, API configuration, voice packages, microphone, dashboard, storage, and safety boundaries |
| *"remind me to stretch in 30 minutes"* | Spoken reminder, background-checked every 15s |
| *"remind me to call mum at 2026-09-10 18:00"* | One-off reminder at an exact time |
| *"delete old_clip.mp4"* | Goes through the permission prompt (test mode) |
| *"quit"* | Shuts down gracefully |

## 🧩 Skills

Skills self-register — drop a module in `skills/` that calls `register_skill()`
and `brain/main.py` picks it up automatically (no central list to edit).
Handlers may take `(user_input)` or `(user_input, gemini_client=None)`.

| Skill | Module | Triggers | Permission |
|---|---|---|---|
| `video_creator` | `skills/video_creator.py` | make/create a video/short… (any niche) | safe |
| `strategy` | `skills/strategy.py` | trending, research…, plan a video… | safe |
| `youtube_publisher` | `skills/youtube_publisher.py` | upload/publish … to youtube | approval_required |
| `roblox_creator` | `skills/roblox_creator.py` | make/create a roblox rant… | safe |
| `idea_generator` | `skills/idea_generator.py` | video ideas, brainstorm… | safe |
| `caption_color` | `skills/video_editor.py` | caption color…, make captions… | safe |
| `project_status` | `skills/project_status.py` | what have you made, my videos… | safe |
| `business_execution` | `skills/business_assistant.py` | execute business idea, start business… | safe for planning; risky tasks require approval; financial tasks blocked |
| `business_tasks` | `skills/business_assistant.py` | show business tasks, approve/reject/complete task… | safe state changes only |
| `system_diagnostics` | `skills/system_diagnostics.py` | check system, run diagnostics… | safe, read-only |
| `test_skill` | `skills/test_skill.py` | activate test skill | safe |

## 🗂️ Project structure

```
jarvis-ai-assistant/
├── brain/main.py          # voice loop: listen → think → speak (+ skills, reminders)
├── core/
│   ├── skill_manager.py   # skill registry, auto-discovery, signature-tolerant calls
│   └── permissions.py     # safe / approval_required / restricted gate
├── skills/                # self-registering capabilities
│   ├── roblox_creator.py  # Short factory orchestration
│   ├── video_editor.py    # trim, assemble, captions, music mix
│   ├── idea_generator.py  # brainstorm video hooks
│   └── project_status.py  # "what have you made?" reporter
├── voice/                 # mic recording, STT, neural TTS + streaming playback
├── memory/                # chat history + Obsidian conversation log
├── tools/scheduler.py     # reminder storage (memory/tasks.json)
├── interface/             # tkinter live status window (optional, headless-safe)
├── workspace/             # footage, music, sfx, scripts, audio, output (see its README)
├── tests/                 # automated tests + manual video checks
└── docs/SETUP.md          # full setup & troubleshooting guide
```

## ⚙️ Configuration (`.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Your key from Google AI Studio |
| `GEMINI_MODEL` | ❌ | `gemini-3.5-flash` | Swap models without touching code |

Other tunables live at the top of their modules: mic levels in `voice/listen.py`
(calibrate with `python voice/calibrate.py`), TTS voice in `voice/speak.py`,
caption style in `skills/video_editor.py`, and the code word in `brain/main.py`.

## 🧪 Tests

```bash
python -m unittest discover tests   # fast, no API key / mic needed
```

Tests needing heavy packages (moviepy, edge-tts) skip themselves when those
aren't installed. Manual end-to-end video checks live in `tests/manual/`.

## 🗺️ Roadmap ideas

Full phased plan: **[Universal Agent Roadmap](docs/ROADMAP.md)**.

- YouTube upload skill (OAuth + `approval_required` permission)
- SFX injection skill using `workspace/sfx/` (vine boom on punchlines 🌿)
- Auto B-roll / facecam overlay support
- Web dashboard replacing the tkinter window
- Wake-word ("Hey JARVIS") instead of push-to-listen

## 🤝 Contributing

Issues and PRs welcome! Please keep skills self-contained in `skills/`,
add a regression test in `tests/test_jarvis.py` when you fix a bug, and run the
suite before pushing.

## 📄 License

MIT — see [LICENSE](LICENSE). Built for fun by Sir Gerald's favorite assistant.
