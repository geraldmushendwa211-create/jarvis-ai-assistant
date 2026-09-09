"""Universal video skill: "make a [niche] short/video about X".

Detects the niche from the command (see core/niches.py), generates a
niche-styled script, and runs the full pipeline: voiceover -> transcribe-once
-> trim -> assemble (9:16 short or 16:9 long-form) -> captions -> SFX ->
music -> QC -> thumbnail -> SEO pack. Every run is tracked as a structured
VideoProject ticket (see core/project.py).

Examples:
    "make a Minecraft short about diamonds"
    "create a gym motivation video"
    "make a 10-minute documentary about black holes"
    "make a horror short about abandoned places, use creepy.mp4"

Notes:
- "Rant" commands still route to the roblox_creator specialist.
- Scripts for factual niches (education, tech) get an automatic
  heuristic fact-check pass; warnings ride along on the ticket.
- Caption style: JARVIS_CAPTION_STYLE=pop|karaoke (default pop).
"""

import asyncio
import os

from core import factcheck, qc, seo
from core.niches import detect_niche
from core.project import VideoProject
from core.skill_manager import register_skill
from voice.speak import _generate_speech_file
from skills.video_editor import (
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    add_background_music,
    add_sfx_track,
    burn_captions,
    create_longform,
    create_short,
    generate_captions,
    transcribe_and_trim,
)

try:
    from interface.status_window import set_state
except ImportError:
    def set_state(state, task_text=""):
        pass

SCRIPTS_DIR = "workspace/scripts"
AUDIO_DIR = "workspace/audio"
FOOTAGE_DIR = "workspace/footage"
LATEST_FILE = os.path.join(OUTPUT_DIR, "latest.txt")
LONG_WORDS = ("long video", "long-form", "longform", "10 minute", "10-minute",
              "documentary", "full video")

# Niches whose scripts get an automatic fact-check pass.
FACT_NICHES = ("education", "tech")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
CAPTION_STYLE = os.getenv("JARVIS_CAPTION_STYLE", "pop")


def _progress(step, detail=""):
    print(f"[video_creator] {step} {detail}".rstrip())
    set_state("EXECUTING", f"{step} {detail}".strip())


def extract_topic(user_input):
    """Pull the video topic out of a command ("about X" / "on X")."""
    lower = user_input.lower()
    if ", use " in lower:
        user_input = user_input[:lower.index(", use ")].strip()
        lower = user_input.lower()
    for keyword in ("about", " on "):
        if keyword in lower:
            return user_input[lower.index(keyword) + len(keyword):].strip()
    return ""


def extract_footage_request(user_input):
    """Return the requested footage filename if the user said 'use <file>'."""
    lower = user_input.lower()
    if "use " not in lower:
        return None
    requested = user_input[lower.index("use ") + len("use "):].strip().strip("'\"")
    requested = requested.split()[0].rstrip(".,!?") if requested else ""
    return requested or None


def is_long_format(user_input):
    return any(w in user_input.lower() for w in LONG_WORDS)


def find_niche_footage(niche, preferred=None):
    """Search workspace/footage (incl. subfolders) for a matching clip.

    Preference order: explicit "use X" request > niche filename hints > any
    clip. Returns (clip_path, error_message); exactly one is None.
    """
    matches = []
    if os.path.isdir(FOOTAGE_DIR):
        for root, _dirs, files in os.walk(FOOTAGE_DIR):
            for f in files:
                if f.lower().endswith(VIDEO_EXTENSIONS):
                    matches.append(os.path.join(root, f))
    matches.sort()
    if not matches:
        return None, (
            f"I couldn't find any footage in {FOOTAGE_DIR} — drop a video "
            f"file ({', '.join(VIDEO_EXTENSIONS)}) in there and try again."
        )
    if preferred:
        hits = [m for m in matches if preferred.lower() in os.path.basename(m).lower()]
        if hits:
            return hits[0], None
        available = ", ".join(os.path.basename(m) for m in matches)
        return None, (f"I couldn't find footage matching '{preferred}'. "
                      f"Available clips: {available}.")
    for hint in niche.footage_hints:
        hits = [m for m in matches if hint in os.path.basename(m).lower()]
        if hits:
            return hits[0], None
    return matches[0], None


def generate_script(topic, niche, video_format, gemini_client):
    if video_format == "long":
        length_rules = (
            "- Long-form video: 8-12 minutes spoken aloud (~1200-1600 words)\n"
            "- Clear sections with spoken transitions "
            "('First...', 'But here's the twist...', 'So what does this mean?')\n"
            "- Re-hook the viewer every ~2 minutes with a payoff or question"
        )
    else:
        length_rules = "- Target length: 30-60 seconds spoken aloud"
    prompt = (
        f"Write a {niche.label} narration script for a YouTube "
        f"{'video' if video_format == 'long' else 'Short'} about: {topic}\n\n"
        f"Tone: {niche.default_tone}\n"
        f"{niche.script_style}\n"
        f"{length_rules}\n"
        "- Write ONLY the spoken narration text, no stage directions, no headers"
    )
    response = gemini_client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def handle_video_creator(user_input, gemini_client=None):
    niche = detect_niche(user_input)
    video_format = "long" if is_long_format(user_input) else "short"
    topic = extract_topic(user_input)

    if not topic:
        return ("What should it be about, Sir Gerald? Try something like: "
                f"make a {niche.label} short about ...")
    if gemini_client is None:
        return "I need access to the AI model to write that script, Sir Gerald. Something's misconfigured."

    project = VideoProject.new(topic, niche=niche.key, format=video_format)
    project.save()

    _progress(f"Writing {niche.label} script...", topic)
    try:
        script_text = generate_script(topic, niche, video_format, gemini_client)
    except Exception as e:
        project.fail(f"script generation: {e}")
        return f"The script generation failed, Sir Gerald: {e}."

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    script_path = os.path.join(SCRIPTS_DIR, f"script_{project.id}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_text)
    project.script = script_text
    project.script_path = script_path
    project.mark("scripted", f"{len(script_text.split())} words")

    # Factual niches get a heuristic claim scan; warnings ride the ticket.
    script_flags = []
    if niche.key in FACT_NICHES:
        script_flags = factcheck.check_text(script_text)
        if script_flags:
            project.fact_check = {"flags": script_flags,
                                  "note": factcheck.summarize(script_flags)}
            project.save()

    _progress("Recording voiceover...")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_path = os.path.join(AUDIO_DIR, f"voiceover_{project.id}.mp3")
    try:
        asyncio.run(_generate_speech_file(script_text, audio_path))
    except Exception as e:
        project.fail(f"voiceover: {e}")
        return (f"I wrote the script, but the voiceover failed, Sir Gerald: {e}. "
                f"Here's the script: {script_text}")
    project.audio_path = audio_path
    project.mark("voiced", os.path.basename(audio_path))

    requested_clip = extract_footage_request(user_input)
    clip_path, clip_error = find_niche_footage(niche, preferred=requested_clip)
    if clip_error:
        project.fail(f"footage: {clip_error}")
        return (f"I've recorded the voiceover, but {clip_error} "
                f"Here's the script: {script_text}")
    project.footage_path = clip_path

    assemble = create_longform if video_format == "long" else create_short
    expect_dims = (1920, 1080) if video_format == "long" else (1080, 1920)
    try:
        _progress("Transcribing + trimming dead space...")
        trimmed_audio_path, words = transcribe_and_trim(audio_path)

        _progress("Assembling video...", os.path.basename(clip_path))
        video_path = assemble(
            trimmed_audio_path,
            output_filename=f"output_{project.id}.mp4",
            footage_path=clip_path,
        )
        if not video_path:
            raise RuntimeError("assembly did not produce a video.")
        project.mark("edited", os.path.basename(video_path))

        _progress("Generating captions...")
        ass_path = generate_captions(
            trimmed_audio_path,
            ass_path=os.path.join(OUTPUT_DIR, f"captions_{project.id}.ass"),
            words=words,
            style=CAPTION_STYLE,
        )
        project.ass_path = ass_path

        _progress("Burning captions...")
        captioned_path = burn_captions(
            video_path,
            ass_path,
            output_filename=f"output_captioned_{project.id}.mp4",
        )
        project.mark("captioned", os.path.basename(captioned_path))

        _progress("Placing sound effects...")
        sfx_path, sfx_count = add_sfx_track(
            captioned_path,
            words,
            output_filename=f"output_sfx_{project.id}.mp4",
        )

        _progress("Mixing background music...")
        final_path = add_background_music(
            sfx_path,
            output_filename=f"output_final_{project.id}.mp4",
        )
        if not final_path:
            raise RuntimeError("add_background_music() did not produce a video.")
    except Exception as e:
        project.fail(f"assembly: {e}")
        return (
            f"I recorded the voiceover and picked footage ({clip_path}), but assembling "
            f"the final video failed, Sir Gerald: {e}. Here's the script: {script_text}"
        )

    project.output_path = final_path
    project.mark("done", final_path)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_path)

    # Post-production: QC gate, thumbnail, SEO pack. None of these can kill
    # an already-finished render — failures degrade to warnings.
    _progress("Running quality control...")
    try:
        qc_result = qc.check_video(final_path, *expect_dims, ass_path=ass_path)
    except Exception as e:
        qc_result = {"passed": False, "checks": [
            {"name": "qc crashed", "ok": False, "detail": str(e)}]}
    project.qc = qc_result
    project.save()

    thumb_path = ""
    try:
        from core.thumbnail import make_thumbnail  # lazy: needs pillow
        _progress("Building thumbnail...")
        thumb_path = make_thumbnail(
            final_path, topic,
            os.path.join(OUTPUT_DIR, f"thumb_{project.id}.jpg"))
        project.thumbnail_path = thumb_path
    except Exception as e:
        print(f"[video_creator] Thumbnail skipped ({e})")

    seo_path = ""
    try:
        _progress("Writing SEO pack...")
        seo_data = seo.generate_seo(topic, niche.label, gemini_client)
        seo_path = seo.write_seo_file(project.id, topic, seo_data)
        seo_data["file"] = seo_path
        project.seo = seo_data
    except Exception as e:
        print(f"[video_creator] SEO pack skipped ({e})")
    project.save()

    kind = "video" if video_format == "long" else "short"
    music_note = ""
    if final_path == sfx_path:
        music_note = "No background music was found, so this one is voiceover-only. "
    flag_note = ""
    if script_flags:
        flag_note = (f"Heads-up: {len(script_flags)} line(s) make strong claims — "
                     f"I've flagged them in the project ticket. ")
    extras = []
    if sfx_count:
        extras.append(f"{sfx_count} sound effects")
    if thumb_path:
        extras.append("thumbnail")
    if seo_path:
        extras.append("SEO pack")
    extra_note = f"Plus: {', '.join(extras)}. " if extras else ""
    qc_note = ""
    if not qc_result.get("passed"):
        qc_note = f"QC flagged: {', '.join(qc.failed_names(qc_result))}. "

    return (
        f"Your {niche.label} {kind} is ready, Sir Gerald — saved to {final_path}. "
        f"{music_note}{flag_note}{extra_note}{qc_note}"
        f"Here's the script: {script_text}"
    )


register_skill(
    name="video_creator",
    triggers=[
        "make a video", "make me a video", "create a video",
        "make a short", "make me a short", "create a short",
        "make a roblox short", "make a minecraft video", "make a minecraft short",
        "make a gym video", "make a horror short", "make a tech video",
        "make a documentary", "create a documentary",
    ],
    handler=handle_video_creator,
    permission_level="safe",
)
