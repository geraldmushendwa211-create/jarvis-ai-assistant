# JARVIS Universal Agent Roadmap

The long-term vision: JARVIS as a modular, local-first YouTube agent system —
plan, create, edit, publish, monitor, and improve content across many niches
and formats (Shorts, long-form, gaming, fitness, education, horror, tech…).

Design law (from the original spec): **do NOT build one giant agent.**

```
JARVIS       = orchestrator (brain/main.py)
SKILLS       = specialists (skills/ + core/ services)
TOOLS        = actual software (FFmpeg, Whisper, SQLite…)
MODELS       = AI intelligence (Gemini today, swappable later)
PROJECT JSON = shared memory per video (core/project.py)
```

## $0-budget rule

Default stack must stay free: Gemini free tier, edge-tts, faster-whisper
(local), imageio-ffmpeg (bundled binary). Paid APIs require explicit user
approval. If a task can't be done free/local, JARVIS explains the limitation
instead of spending money.

## Conventions for new agents/slices

1. **One video = one `VideoProject` ticket** (`workspace/projects/<id>.json`).
   Every stage reads/writes it via `mark()` / `fail()` — no random text
   handoffs between stages.
2. **New verticals = niche profiles** (`core/niches.py`), not new pipelines.
3. **New capabilities = skills** (`skills/` + `register_skill()`), auto-discovered.
4. **Risky actions = permission levels** (`core/permissions.py`); uploads and
   auto-publish default to `approval_required`.
5. **Every slice ships with tests** in `tests/` and docs updates.

---

## Phase 0 — DONE ✅ (foundation)

- Voice loop, Gemini chat, streaming TTS, reminders, Obsidian memory
- Skill registry + auto-discovery, permission gate, status window
- Roblox Short pipeline (script → voice → trim → captions → music)
- Idea generator, caption colors, project status, 16+ regression tests
- README, setup guide, repo hygiene

## Phase 1 — Universal foundation ✅ (this slice)

- `core/niches.py`: 9 profiles (roblox, minecraft, gaming, fitness, horror,
  tech, education, motivation, generic) — config, not code
- `core/project.py`: structured `VideoProject` job tickets (JSON, SQLite-ready)
- `skills/video_creator.py`: *"make a [niche] short/video about X"* for any niche
- Long-form produces script + voiceover now; 16:9 assembly is Phase 3

## Phase 2 — Strategy & script depth ✅ DONE

- `core/trends.py`: keyless trend discovery (per-niche Reddit subs + HN for tech)
- `core/research.py`: Wikipedia + DuckDuckGo fact briefs, saved into the ticket
- `skills/strategy.py`: *"what's trending"*, *"research X"*,
  *"plan a video about X"* → research + ideas (difficulty + why) + scored
  titles + plan file + ticket
- `core/hooks.py`: deterministic title scorer (0–100) with regenerate-if-weak loop
- `core/factcheck.py`: superlative/absolute/number scanner; auto-runs on
  education + tech scripts inside `video_creator`

## Phase 3 — Editing & QC ✅ DONE

- Whisper once per video: `transcribe_and_trim()` + cached model + timestamp
  remapping (`core/captions.py`) — roughly halves AI wait on CPU-only PCs
- 16:9 long-form assembly (`create_longform`) next to `create_short`
- `JARVIS_RENDER_PRESET` (default `veryfast`): 2–3× faster encodes on older CPUs
- Auto SFX (`core/sfx.py` + `add_sfx_track`): punch words trigger meme sounds
- Karaoke captions (`JARVIS_CAPTION_STYLE=karaoke`): active-word highlighting
- `core/thumbnail.py`: 1280×720 frame + bold title card (Arial Black on Windows)
- `core/seo.py`: title + Gemini description + hashtags, saved per video
- `core/qc.py`: resolution/duration/audio/captions gate on every render,
  results stored on the project ticket

## Phase 4 — Publish & approval

- YouTube API OAuth (secure token store, never passwords) + upload skill
- Human approval modes: manual / approve-each / scheduled-auto
- Scheduler: *"upload Mon/Wed/Fri at 7 PM"* queue with retries
- Repurposing: long video → N Shorts (scene detection + reframe)

## Phase 5 — Analytics & learning

- Analytics pull (views, retention, CTR) into per-video ticket fields
- Performance analysis: *"tutorials beat news 3:1 in your last 20"*
- Learning loop: feed winners back into strategy + idea ranking
- Comment digest: fetch, classify, draft replies (never auto-post w/o permission)

## Phase 6 — Scale

- Multi-channel profiles (niche + branding + schedule per channel)
- Localization: translate script → re-voice (Swahili/French/Spanish…)
- Central SQLite DB migration (same `VideoProject` fields)
- Web dashboard (status, transcript, skill buttons, gallery, phone control)

## Phase 7 — Local-first models

- LLM provider seam (`core/llm.py`): Gemini today, Ollama/Qwen optional
- Local TTS (Piper/Kokoro) as offline voice option
- Wake word + barge-in; function-calling brain (Gemini picks skills itself)
