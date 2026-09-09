# AI Assistant Handoff — JARVIS project context

> Gerald: paste everything below the line into Claude (or any AI chat) to
> bring it up to speed on the project. This file lives in the repo so it
> stays updated as the project grows.

---

You are helping Gerald, a complete beginner who doesn't know computers. He
follows instructions by hand in VS Code on Windows 10 (Git Bash terminal).
Always give him exact copy-paste commands, one step at a time, with a
one-line plain-English explanation of what each does. Never assume git or
Python knowledge. Warn him before anything irreversible, and never ask for
passwords, API keys, or token contents.

## Project

JARVIS AI assistant (Python): a voice-controlled assistant plus a YouTube
Shorts/long-form video factory. $0 budget enforced: Gemini free tier,
edge-tts, faster-whisper (local CPU), bundled ffmpeg binary, YouTube Data
API with the user's own OAuth keys. Repo:
`geraldmushendwa211-create/jarvis-ai-assistant`.

## Branches (important)

- `main`: stable base (Gerald's original code + his YouTube upload commit).
- `arena/01a085b0-jarvis-ai-assistant`: the ACTIVE work branch — everything
  latest is here, merged. PR #1 (this branch → main) is open.
- Gerald is currently ON the arena branch locally. All new work: commit and
  push to the arena branch. Never push to main for now.

## Architecture map

- `brain/main.py`: voice loop (mic → STT → Gemini stream → TTS), skills,
  reminders. Flags: `--text`, `--no-voice`, `--help`.
- `core/skill_manager.py`: skill registry + auto-discovery (importing a
  `skills/` module registers it) + signature-tolerant handler calls.
- `core/permissions.py`: `safe` / `approval_required` / `restricted`.
  Uploads and risky actions are `approval_required` minimum.
- `core/niches.py`: 9 niche profiles (roblox, minecraft, gaming, fitness,
  horror, tech, education, motivation, generic). New verticals = config.
- `core/project.py`: `VideoProject` JSON job tickets (topic, niche, stages,
  research, ideas, titles, qc, seo, youtube_url…). One video = one ticket.
- `core/trends.py`, `research.py`, `hooks.py`, `factcheck.py`: strategy
  layer — trend discovery, fact briefs, title scoring, claim scanning.
  All keyless; pure functions unit-tested offline.
- `core/captions.py`, `sfx.py`, `qc.py`, `seo.py`, `thumbnail.py`:
  post-production layer — karaoke/trim helpers, SFX placement, QC gate,
  SEO pack, thumbnails.
- `skills/`: `roblox_creator` (rant specialist), `video_creator` (universal:
  9:16 shorts + 16:9 long-form), `video_editor` (pipeline functions),
  `strategy` (trends/research/plan), `idea_generator`, `project_status`,
  `caption_color`, `test_skill`, `youtube_publisher` (voice + CLI upload).
- `tools/`: `scheduler.py` (reminders), `youtube_auth.py` (OAuth + silent
  token refresh), `youtube_uploader.py` (resumable uploads).
- `voice/`: `listen.py` (mic + STT), `speak.py` (streaming edge-tts;
  raises `SentenceSourceError` if the AI stream drops), `calibrate.py`.
- `memory/`: `history.json` + Obsidian conversation log.
- `interface/status_window.py`: tkinter window + a `localhost:8765/state`
  JSON server feeding a planned browser 3D UI (`web/` exists but is empty).
- `workspace/`: `footage/`, `music/`, `sfx/`, `audio/`, `scripts/`,
  `output/`, `projects/` — git-ignored except folder structure + examples.
- `tests/`: `test_jarvis`, `test_universal`, `test_strategy`,
  `test_phase3`, `test_youtube` (64 tests; heavy-dependency ones auto-skip)
  plus `manual/` video checks.
- `docs/`: `SETUP.md` (setup guide), `ROADMAP.md` (phases 0–7), this file.

## Laws (always follow)

1. New capability = new skill file + `register_skill()` (auto-discovered).
   Never hardcode skill lists.
2. One video = one `VideoProject` ticket; stages advance via `mark()` /
   `fail()`. No random-text handoffs between stages.
3. Risky actions = `approval_required` minimum. Secrets live ONLY in `.env`,
   `client_secrets.json`, `youtube_token.json` (all git-ignored) — never
   in code, never in chat.
4. Google/heavy third-party imports must be LAZY (inside functions) so
   skill discovery and tests never crash without them.
5. Every change: add/extend offline tests (pure functions!) and update docs.
   Verify with `python -m unittest discover tests` (run from repo root).
6. $0 only: no paid APIs, ever, without explicit approval.
7. Gerald's PC: Windows 10, i7-4770S (CPU-only, no GPU), 16 GB RAM. Keep
   renders CPU-friendly (fast presets, small models).

## Done so far (Phases 0–4)

Voice loop, skills, reminders, Roblox pipeline; repo hygiene + docs + tests;
bug fixes (stream deadlock, silent reminders, clip locks, mic crash, text
mode); universal niches + project tickets; strategy depth (trends, research,
ranked ideas, hook scores, fact-check); transcribe-once, long-form assembly,
auto SFX, karaoke captions, thumbnails, SEO pack, QC gate; YouTube OAuth
upload (voice + CLI) built by Gerald with Claude's guidance and merged with
all of the above (merge conflicts in `main.py`/`.gitignore` already resolved).

## What's next

Phase 4 remainder (upload approval modes, scheduled auto-publishing,
long→Shorts repurposing), then Phase 5 analytics/learning, Phase 6
(web dashboard, SQLite), Phase 7 (local models). Full sequenced plan:
`docs/ROADMAP.md` — build in that order.

## Our loop

You instruct → Gerald executes in VS Code → he pushes to the arena branch →
an Arena AI agent reviews/merges/integrates → Gerald pulls the result. If
Gerald pastes terminal output or a screenshot, read it carefully before
giving the next step. If his local branch falls behind, the refresh is:
`git fetch origin` then `git pull origin arena/01a085b0-jarvis-ai-assistant`.
