"""Universal video skill: "make a [niche] short/video about X".

Detects the niche from the command (see core/niches.py), generates a
niche-styled script, and runs the standard Short pipeline. Every run is
tracked as a structured VideoProject ticket (see core/project.py).

Examples:
    "make a Minecraft short about diamonds"
    "create a gym motivation video"
    "make a horror short about abandoned places, use creepy.mp4"

Notes:
- "Rant" commands still route to the roblox_creator specialist.
- Long-form (10-minute / documentary) currently produces the script +
  voiceover and stops with a clear message — 16:9 assembly is next.
"""

import asyncio
import os

from core.niches import detect_niche
from core.project import VideoProject
from core.skill_manager import register_skill
from voice.speak import _generate_speech_file
from skills.video_editor import (
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    add_background_music,
    burn_captions,
    create_short,
    generate_captions,
    trim_dead_space,
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

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


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

    if video_format == "long":
        # 16:9 long-form assembly lands in the next slice — but the script and
        # voiceover are real, saved, and tracked on the project ticket.
        return (
            f"The {niche.label} script and voiceover are ready, Sir Gerald — "
            f"script at {script_path}, audio at {audio_path}. Long-form video "
            f"assembly (16:9) is still being built; ask me for a Short and "
            f"I'll render the full video today."
        )

    requested_clip = extract_footage_request(user_input)
    clip_path, clip_error = find_niche_footage(niche, preferred=requested_clip)
    if clip_error:
        project.fail(f"footage: {clip_error}")
        return (f"I've recorded the voiceover, but {clip_error} "
                f"Here's the script: {script_text}")
    project.footage_path = clip_path

    try:
        _progress("Trimming dead space...")
        trimmed_audio_path = trim_dead_space(audio_path)

        _progress("Assembling video...", os.path.basename(clip_path))
        video_path = create_short(
            trimmed_audio_path,
            output_filename=f"output_{project.id}.mp4",
            footage_path=clip_path,
        )
        if not video_path:
            raise RuntimeError("create_short() did not produce a video.")
        project.mark("edited", os.path.basename(video_path))

        _progress("Generating captions...")
        ass_path = generate_captions(
            trimmed_audio_path,
            ass_path=os.path.join(OUTPUT_DIR, f"captions_{project.id}.ass"),
        )
        project.ass_path = ass_path

        _progress("Burning captions...")
        captioned_path = burn_captions(
            video_path,
            ass_path,
            output_filename=f"output_captioned_{project.id}.mp4",
        )
        project.mark("captioned", os.path.basename(captioned_path))

        _progress("Mixing background music...")
        final_path = add_background_music(
            captioned_path,
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

    music_note = ""
    if final_path == captioned_path:
        music_note = "No background music was found, so this one is voiceover-only. "

    return (
        f"Your {niche.label} short is ready, Sir Gerald — saved to {final_path}. "
        f"{music_note}Here's the script: {script_text}"
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
