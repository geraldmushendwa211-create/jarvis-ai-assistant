import os
import random
import asyncio
from datetime import datetime
from core.skill_manager import register_skill
from voice.speak import _generate_speech_file
from skills.video_editor import (
    trim_dead_space,
    create_short,
    generate_captions,
    burn_captions,
    add_background_music,
    OUTPUT_DIR,
)

SCRIPTS_DIR = "workspace/scripts"
AUDIO_DIR = "workspace/audio"
FOOTAGE_DIR = "workspace/footage"
VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi")


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
        model="gemini-3.5-flash",
        contents=prompt,
    )
    return response.text.strip()


def pick_gameplay_clip():
    os.makedirs(FOOTAGE_DIR, exist_ok=True)
    candidates = [
        f for f in os.listdir(FOOTAGE_DIR)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    ]
    if not candidates:
        return None
    chosen = random.choice(candidates)
    return os.path.join(FOOTAGE_DIR, chosen)


def handle_roblox_creator(user_input, gemini_client=None):
    lower = user_input.lower()
    if "about" in lower:
        topic = user_input[lower.index("about") + len("about"):].strip()
    else:
        topic = user_input

    if gemini_client is None:
        return "I need access to the AI model to write that script, Sir Gerald. Something's misconfigured."

    script_text = generate_script(topic, gemini_client)

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    script_path = os.path.join(SCRIPTS_DIR, f"script_{timestamp}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    audio_path = os.path.join(AUDIO_DIR, f"voiceover_{timestamp}.mp3")
    try:
        asyncio.run(_generate_speech_file(script_text, audio_path))
    except Exception as e:
        return f"I wrote the script, but the voiceover recording failed, Sir Gerald: {e}. Here's the script: {script_text}"

    clip_path = pick_gameplay_clip()
    if not clip_path:
        return (
            f"I've recorded the voiceover, but couldn't find any gameplay footage in "
            f"workspace/footage — drop a video file in there and try again. "
            f"Here's the script: {script_text}"
        )

    # Assemble the final video: trim dead space out of the voiceover, combine
    # it with the gameplay footage, burn on styled captions, then mix in
    # background music underneath.
    try:
        trimmed_audio_path = trim_dead_space(audio_path)

        video_path = create_short(
            trimmed_audio_path,
            output_filename=f"output_{timestamp}.mp4",
            footage_path=clip_path,
        )
        if not video_path:
            raise RuntimeError("create_short() did not produce a video.")

        ass_path = generate_captions(
            trimmed_audio_path,
            ass_path=os.path.join(OUTPUT_DIR, f"captions_{timestamp}.ass"),
        )

        captioned_path = burn_captions(
            video_path,
            ass_path,
            output_filename=f"output_captioned_{timestamp}.mp4",
        )

        final_path = add_background_music(
            captioned_path,
            output_filename=f"output_final_{timestamp}.mp4",
        )
        if not final_path:
            raise RuntimeError("add_background_music() did not produce a video.")

    except Exception as e:
        return (
            f"I recorded the voiceover and picked footage ({clip_path}), but assembling "
            f"the final video failed, Sir Gerald: {e}. Here's the script: {script_text}"
        )

    return (
        f"Your Roblox rant short is ready, Sir Gerald — saved to {final_path}. "
        f"Here's the script: {script_text}"
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