"""Roblox rant Short factory: script -> voiceover -> captioned vertical video.

Voice commands (examples):
    "make a Roblox rant about admin abusers"
    "create a Roblox rant on pay-to-win games"
    "make a Roblox rant about campers, use parkour.mp4"

Saying "use <filename>" picks a specific clip from workspace/footage instead
of a random one. The voiceover is transcribed once and the timings are reused
for trimming, captions, and SFX placement.
"""

import os
import random
import asyncio
from datetime import datetime
from core import qc
from core.skill_manager import register_skill
from voice.speak import _generate_speech_file
from skills.video_editor import (
    add_background_music,
    add_sfx_track,
    burn_captions,
    create_short,
    generate_captions,
    transcribe_and_trim,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
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

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
CAPTION_STYLE = os.getenv("JARVIS_CAPTION_STYLE", "pop")


def _progress(step, detail=""):
    print(f"[roblox_creator] {step} {detail}".rstrip())
    set_state("EXECUTING", f"{step} {detail}".strip())


def generate_script(topic, gemini_client):
    prompt = (
        f"Write a Roblox rant script for a YouTube Short about: {topic}\n\n"
        "Style rules:\n"
        "- Strong hook in the first line\n"
        "- Fast pacing, short sentences\n"
        "- Humor, exaggeration, relatability\n"
        "- Punchy, memorable ending\n"
        "- Target length: 30-60 seconds spoken aloud\n"
        "- Write ONLY the spoken narration text, no stage directions, no headers"
    )
    response = gemini_client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    return response.text.strip()


def extract_topic(user_input):
    """Pull the rant topic out of a voice command.

    Handles "... about X", "... on X", and falls back to everything after
    the trigger verb. Strips a trailing ", use <file>" footage request.
    """
    text = user_input
    lower = text.lower()
    if ", use " in lower:
        text = text[:lower.index(", use ")].strip()
        lower = text.lower()
    for keyword in ("about", " on "):
        if keyword in lower:
            topic = text[lower.index(keyword) + len(keyword):].strip()
            if topic:
                return topic
    # Fallback: drop the leading verb ("make/create ... rant").
    for verb in ("make a roblox rant", "create a roblox rant",
                 "make a roblox rent", "create a roblox rent",
                 "roblox rant", "roblox rent"):
        if lower.startswith(verb):
            topic = text[len(verb):].strip()
            if topic:
                return topic
    return text.strip()


def extract_footage_request(user_input):
    """Return the requested footage filename if the user said 'use <file>'."""
    lower = user_input.lower()
    if "use " not in lower:
        return None
    requested = user_input[lower.index("use ") + len("use "):].strip().strip("'\"")
    # Take just the filename in case of trailing words/punctuation.
    requested = requested.split()[0].rstrip(".,!?") if requested else ""
    return requested or None


def pick_gameplay_clip(preferred=None):
    """Pick a gameplay clip. Prefers `preferred` (fuzzy filename match).

    Returns (clip_path, error_message). Exactly one of them is None.
    """
    os.makedirs(FOOTAGE_DIR, exist_ok=True)
    candidates = sorted(
        f for f in os.listdir(FOOTAGE_DIR)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    )
    if not candidates:
        return None, (
            f"I couldn't find any gameplay footage in {FOOTAGE_DIR} — "
            f"drop a video file ({', '.join(VIDEO_EXTENSIONS)}) in there and try again."
        )
    if preferred:
        matches = [c for c in candidates if preferred.lower() in c.lower()]
        if matches:
            return os.path.join(FOOTAGE_DIR, matches[0]), None
        available = ", ".join(candidates)
        return None, (
            f"I couldn't find footage matching '{preferred}'. "
            f"Available clips: {available}."
        )
    chosen = random.choice(candidates)
    return os.path.join(FOOTAGE_DIR, chosen), None


def handle_roblox_creator(user_input, gemini_client=None):
    topic = extract_topic(user_input)
    if gemini_client is None:
        return "I need access to the AI model to write that script, Sir Gerald. Something's misconfigured."

    _progress("Writing script...", topic)
    script_text = generate_script(topic, gemini_client)

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    script_path = os.path.join(SCRIPTS_DIR, f"script_{timestamp}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    _progress("Recording voiceover...")
    audio_path = os.path.join(AUDIO_DIR, f"voiceover_{timestamp}.mp3")
    try:
        asyncio.run(_generate_speech_file(script_text, audio_path))
    except Exception as e:
        return f"I wrote the script, but the voiceover recording failed, Sir Gerald: {e}. Here's the script: {script_text}"

    requested_clip = extract_footage_request(user_input)
    clip_path, clip_error = pick_gameplay_clip(preferred=requested_clip)
    if clip_error:
        return (
            f"I've recorded the voiceover, but {clip_error} "
            f"Here's the script: {script_text}"
        )

    # Assemble the final video: transcribe once, trim dead space, combine with
    # gameplay footage, burn styled captions, place meme SFX, then mix in
    # background music underneath (skipped gracefully if none is found).
    try:
        _progress("Transcribing + trimming dead space...")
        trimmed_audio_path, words = transcribe_and_trim(audio_path)

        _progress("Assembling video...", os.path.basename(clip_path))
        video_path = create_short(
            trimmed_audio_path,
            output_filename=f"output_{timestamp}.mp4",
            footage_path=clip_path,
        )
        if not video_path:
            raise RuntimeError("create_short() did not produce a video.")

        _progress("Generating captions...")
        ass_path = generate_captions(
            trimmed_audio_path,
            ass_path=os.path.join(OUTPUT_DIR, f"captions_{timestamp}.ass"),
            words=words,
            style=CAPTION_STYLE,
        )

        _progress("Burning captions...")
        captioned_path = burn_captions(
            video_path,
            ass_path,
            output_filename=f"output_captioned_{timestamp}.mp4",
        )

        _progress("Placing sound effects...")
        sfx_path, sfx_count = add_sfx_track(
            captioned_path,
            words,
            output_filename=f"output_sfx_{timestamp}.mp4",
        )

        _progress("Mixing background music...")
        final_path = add_background_music(
            sfx_path,
            output_filename=f"output_final_{timestamp}.mp4",
        )
        if not final_path:
            raise RuntimeError("add_background_music() did not produce a video.")

    except Exception as e:
        return (
            f"I recorded the voiceover and picked footage ({clip_path}), but assembling "
            f"the final video failed, Sir Gerald: {e}. Here's the script: {script_text}"
        )

    # Remember the newest render for the project_status skill.
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        f.write(final_path)

    music_note = ""
    if final_path == sfx_path:
        music_note = "No background music was found, so this one is voiceover-only. "

    sfx_note = f"Plus {sfx_count} sound effects. " if sfx_count else ""

    qc_note = ""
    try:
        qc_result = qc.check_video(final_path, 1080, 1920, ass_path=ass_path)
        if not qc_result.get("passed"):
            qc_note = f"QC flagged: {', '.join(qc.failed_names(qc_result))}. "
    except Exception as e:
        print(f"[roblox_creator] QC skipped ({e})")

    return (
        f"Your Roblox rant short is ready, Sir Gerald — saved to {final_path}. "
        f"{music_note}{sfx_note}{qc_note}Here's the script: {script_text}"
    )


register_skill(
    name="roblox_creator",
    triggers=[
        "make a roblox rant", "create a roblox rant", "roblox rant about",
        "make a roblox rent", "create a roblox rent", "roblox rent video",
        "make a roblox ran", "create a roblox ran",
    ],
    handler=handle_roblox_creator,
    permission_level="safe",
)
