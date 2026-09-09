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

## Phase 2 — Strategy & script depth (next)

- Trend discovery: free sources (YouTube RSS/search, Reddit) → ranked topics
- Research agent: gather facts + sources into the project ticket
- Idea agent upgrade: difficulty + "why it may work" per idea (ticket fields)
- Hook/title agent: N titles + hook score, rewrite loop before scripting
- Fact-check pass for education/news niches (flag unsupported claims)

## Phase 3 — Editing & QC

- 16:9 long-form assembly (landscape pipeline next to `create_short`)
- SFX punchlines from `workspace/sfx/` on emotional beats
- Karaoke word-highlight captions; thumbnail generator (PIL)
- SEO/metadata pack: title, description, hashtags, chapters
- QC agent: resolution, duration, audio levels, missing assets → fix loop
- Whisper once per video (transcribe once, reuse timings everywhere)

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
