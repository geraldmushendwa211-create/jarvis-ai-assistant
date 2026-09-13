import os
import glob
import subprocess
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from faster_whisper import WhisperModel
from pydub import AudioSegment
import imageio_ffmpeg
from core.captions import (chunk_words, compute_keep_segments, karaoke_events,
                           remap_words)
from core.sfx import pick_moments as pick_sfx_moments
from core.skill_manager import register_skill

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
FOOTAGE_DIR = os.path.join(WORKSPACE_DIR, "footage")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
LANDSCAPE_WIDTH = 1920
LANDSCAPE_HEIGHT = 1080

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm")

# Rendering: "veryfast" suits older CPUs (e.g. i7-4770) with negligible quality
# loss for Shorts. Set JARVIS_RENDER_PRESET=medium|slow for maximum quality.
RENDER_PRESET = os.getenv("JARVIS_RENDER_PRESET", "veryfast")

CAPTION_COLORS = {
    "gold":   "&H0000D7FF",
    "white":  "&H00FFFFFF",
    "red":    "&H000000FF",
    "cyan":   "&H00FFFF00",
    "green":  "&H0014FF39",
    "pink":   "&H00AD3DFF",
    "purple": "&H00FF26B0",
}

CURRENT_CAPTION_COLOR = "gold"
CURRENT_CAPTION_STYLE = "pop"  # pop | karaoke

_WHISPER_MODEL = None


def _get_whisper_model():
    """Load the Whisper model once per session instead of per call."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        print("Loading Whisper model (once per session)...")
        _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def find_footage_clip():
    """Find the first video file in workspace/footage (any supported format)."""
    if not os.path.exists(FOOTAGE_DIR):
        return None
    video_files = []
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(glob.glob(os.path.join(FOOTAGE_DIR, f"*{ext}")))
    if not video_files:
        return None
    return sorted(video_files)[0]


def resize_to_fill(clip, width, height):
    """Crop/resize a clip to fill a width x height frame."""
    clip_ratio = clip.w / clip.h
    target_ratio = width / height

    if clip_ratio > target_ratio:
        clip = clip.resized(height=height)
        clip = clip.cropped(x_center=clip.w / 2, width=width)
    else:
        clip = clip.resized(width=width)
        clip = clip.cropped(y_center=clip.h / 2, height=height)

    return clip


def resize_to_vertical(clip):
    """Crop/resize a clip to fill a 1080x1920 vertical frame."""
    return resize_to_fill(clip, TARGET_WIDTH, TARGET_HEIGHT)


def transcribe_words(voiceover_path):
    """Transcribe voiceover_path with faster-whisper, return word timings."""
    model = _get_whisper_model()
    segments, _ = model.transcribe(voiceover_path, word_timestamps=True)
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({"word": word.word.strip(), "start": word.start, "end": word.end})
    return words


def generate_captions(voiceover_path, ass_path=None, color=None, words=None, style=None):
    """
    Transcribe the voiceover (unless word timings are passed in) and write a
    stylized ASS caption file. style: "pop" (default) or "karaoke".
    """
    if ass_path is None:
        ass_path = os.path.join(OUTPUT_DIR, "captions.ass")

    if color is None:
        color = CURRENT_CAPTION_COLOR

    if style is None:
        style = CURRENT_CAPTION_STYLE

    primary_colour = CAPTION_COLORS.get(color, CAPTION_COLORS["gold"])

    if words is None:
        words = transcribe_words(voiceover_path)

    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h:01}:{m:02}:{s:02}.{cs:02}"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Caption,Arial Black,90,{primary_colour},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,60,60,220,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header)
        if style == "karaoke":
            for event in karaoke_events(chunk_words(words)):
                f.write(event + "\n")
        else:
            for w in words:
                start = format_time(w["start"])
                end = format_time(w["end"])
                text = w["word"].upper()
                line = (
                    f"Dialogue: 0,{start},{end},Caption,,0,0,0,,"
                    f"{{\\fscx60\\fscy60\\t(0,90,\\fscx100\\fscy100)}}{text}\n"
                )
                f.write(line)

    print(f"Styled captions ({color}/{style}) saved to: {ass_path}")
    return ass_path


def handle_caption_color_command(user_input):
    global CURRENT_CAPTION_COLOR
    text = user_input.lower()

    for color_name in CAPTION_COLORS:
        if color_name in text:
            CURRENT_CAPTION_COLOR = color_name
            return f"Got it, captions will be {color_name} from now on."

    available = ", ".join(CAPTION_COLORS.keys())
    return f"I didn't catch a color in that. Try one of: {available}."


def trim_dead_space(voiceover_path, output_filename=None, max_gap=0.4, padding=0.05, words=None):
    """
    Removes excess silence between spoken words in the voiceover.
    Pass words= to reuse an existing transcription instead of re-running Whisper.
    """
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

    if words is None:
        words = transcribe_words(voiceover_path)
    if not words:
        print("No words detected — skipping trim.")
        return voiceover_path

    audio = AudioSegment.from_file(voiceover_path)
    keep_segments = compute_keep_segments(words, len(audio), max_gap, padding)

    trimmed = AudioSegment.empty()
    total_ms = len(audio)
    for start, end in keep_segments:
        start_ms = max(0, int(start * 1000))
        end_ms = min(total_ms, int(end * 1000))
        if end_ms > start_ms:
            trimmed += audio[start_ms:end_ms]

    if output_filename is None:
        base, ext = os.path.splitext(os.path.basename(voiceover_path))
        output_filename = f"{base}_trimmed.mp3"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    trimmed.export(output_path, format="mp3")

    removed = (total_ms / 1000) - (len(trimmed) / 1000)
    print(f"Trimmed {removed:.2f}s of dead space. Saved to: {output_path}")
    return output_path


def transcribe_and_trim(voiceover_path, output_filename=None, max_gap=0.4, padding=0.05):
    """Transcribe ONCE, trim the audio, and remap word timings to fit.

    Returns (trimmed_audio_path, words) where words are timed against the
    TRIMMED audio — ready for captions and SFX with no second Whisper pass.
    """
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

    words = transcribe_words(voiceover_path)
    if not words:
        print("No words detected — skipping trim.")
        return voiceover_path, []

    audio = AudioSegment.from_file(voiceover_path)
    total_ms = len(audio)
    keep_segments = compute_keep_segments(words, total_ms, max_gap, padding)

    trimmed = AudioSegment.empty()
    for start, end in keep_segments:
        start_ms = max(0, int(start * 1000))
        end_ms = min(total_ms, int(end * 1000))
        if end_ms > start_ms:
            trimmed += audio[start_ms:end_ms]

    if output_filename is None:
        base, ext = os.path.splitext(os.path.basename(voiceover_path))
        output_filename = f"{base}_trimmed.mp3"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    trimmed.export(output_path, format="mp3")

    removed = (total_ms / 1000) - (len(trimmed) / 1000)
    print(f"Trimmed {removed:.2f}s of dead space. Saved to: {output_path}")
    return output_path, remap_words(words, keep_segments)


def _assemble_video(voiceover_path, footage_path, width, height, output_filename):
    """Core assembly: loop/trim footage to voiceover length, fill the frame,
    attach audio, encode. Clips always closed (Windows file locks)."""
    voiceover = AudioFileClip(voiceover_path)
    source = VideoFileClip(footage_path)
    try:
        voice_duration = voiceover.duration
        print(f"Voiceover duration: {voice_duration:.2f}s")

        if source.duration < voice_duration:
            loops_needed = int(voice_duration // source.duration) + 1
            assembled = concatenate_videoclips([source] * loops_needed)
        else:
            assembled = source
        try:
            final = resize_to_fill(assembled.subclipped(0, voice_duration), width, height)
            final = final.with_audio(voiceover)

            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            final.write_videofile(output_path, fps=30, codec="libx264",
                                  audio_codec="aac", preset=RENDER_PRESET)
        finally:
            if assembled is not source:
                assembled.close()
    finally:
        source.close()
        voiceover.close()

    print(f"Video saved to: {output_path}")
    return output_path


def create_short(voiceover_path, output_filename="output_short.mp4", footage_path=None):
    """
    Assembles a vertical 1080x1920 short by trimming/looping footage to match
    the voiceover length. footage_path lets a caller specify exactly which
    clip to use; if not given, falls back to find_footage_clip().
    """
    if footage_path is None:
        footage_path = find_footage_clip()
    if not footage_path:
        print("No footage found in workspace/footage. Add a video clip first.")
        return None

    print(f"Using footage: {footage_path}")
    return _assemble_video(voiceover_path, footage_path,
                           TARGET_WIDTH, TARGET_HEIGHT, output_filename)


def create_longform(voiceover_path, output_filename="output_longform.mp4", footage_path=None):
    """
    Assembles a landscape 1920x1080 long-form video. Same contract as
    create_short (caller may pass footage_path; falls back to find_footage_clip).
    """
    if footage_path is None:
        footage_path = find_footage_clip()
    if not footage_path:
        print("No footage found in workspace/footage. Add a video clip first.")
        return None

    print(f"Using footage: {footage_path}")
    return _assemble_video(voiceover_path, footage_path,
                           LANDSCAPE_WIDTH, LANDSCAPE_HEIGHT, output_filename)


def burn_captions(video_path, ass_path, output_filename="output_with_captions.mp4"):
    """Burn the styled ASS captions directly onto the video using ffmpeg's ass filter."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
    vf_arg = f"ass='{escaped_ass}'"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vf", vf_arg,
        "-c:a", "copy",
        output_path,
    ]

    print("Burning styled captions onto video...")
    subprocess.run(cmd, check=True)

    print(f"Captioned video saved to: {output_path}")
    return output_path


def add_sfx_track(video_path, words, sfx_dir=None, output_filename="output_with_sfx.mp4",
                  volume=0.4, max_events=6):
    """Auto-place meme SFX (vine boom, bruh...) on punchy words.

    Returns (path, event_count). If no moments match or no SFX files exist,
    the original video is returned untouched with count 0 — never a failure.
    """
    if sfx_dir is None:
        sfx_dir = os.path.join(WORKSPACE_DIR, "sfx")
    moments = pick_sfx_moments(words or [], sfx_dir, max_events=max_events)
    if not moments:
        return video_path, 0

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    cmd = [ffmpeg_exe, "-y", "-i", video_path]
    for _, sfx_path in moments:
        cmd += ["-i", sfx_path]

    parts = []
    mix_inputs = ["[0:a]"]
    for i, (sec, _sfx_path) in enumerate(moments, start=1):
        ms = int(sec * 1000)
        parts.append(f"[{i}:a]adelay={ms}|{ms},volume={volume}[s{i}]")
        mix_inputs.append(f"[s{i}]")
    parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}"
                 f":duration=first:dropout_transition=0:normalize=0[aout]")
    cmd += ["-filter_complex", ";".join(parts),
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", output_path]

    print(f"Mixing {len(moments)} sound effects into video...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg sfx error:", result.stderr[-800:])
        print("[JARVIS] SFX mix failed — keeping the video without sound effects.")
        return video_path, 0

    print(f"Video with SFX saved to: {output_path}")
    return output_path, len(moments)


def _get_mean_volume_db(path, ffmpeg_exe):
    """Runs ffmpeg's volumedetect filter and returns the mean loudness in dB, or None if it can't be read."""
    cmd = [ffmpeg_exe, "-i", path, "-af", "volumedetect", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stderr.splitlines():
        if "mean_volume:" in line:
            try:
                value = line.split("mean_volume:")[1].strip().split(" ")[0]
                return float(value)
            except (IndexError, ValueError):
                return None
    return None


def add_background_music(video_path, music_path=None, output_filename="output_with_music.mp4",
                          music_volume=None, target_offset_db=14):
    """
    Mixes a background music track underneath the video's existing voiceover
    audio, auto-leveling the music volume against the actual measured loudness.

    Background music is optional: if no track is found, the original video is
    returned unchanged (with a warning) instead of failing the whole pipeline.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if music_path is None:
        music_path = os.path.join(WORKSPACE_DIR, "music", "background_music.mp3")

    if not os.path.exists(music_path):
        print(f"[JARVIS] No background music found at {music_path} — "
              f"keeping voiceover-only audio.")
        return video_path

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with AudioFileClip(video_path) as clip:
        video_duration = clip.duration
    fade_start = max(video_duration - 2, 0)

    if music_volume is None:
        voice_db = _get_mean_volume_db(video_path, ffmpeg_exe)
        music_db = _get_mean_volume_db(music_path, ffmpeg_exe)
        if voice_db is not None and music_db is not None:
            target_db = voice_db - target_offset_db
            music_volume = 10 ** ((target_db - music_db) / 20)
            music_volume = max(0.05, min(music_volume, 1.0))
            print(f"Auto-level: voice ~{voice_db:.1f}dB, music ~{music_db:.1f}dB -> using volume {music_volume:.2f}")
        else:
            music_volume = 0.15
            print("Couldn't measure volume automatically, falling back to default 0.15")

    filter_complex = (
        f"[1:a]volume={music_volume},afade=t=in:st=0:d=2,"
        f"afade=t=out:st={fade_start}:d=2[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        output_path,
    ]

    print("Mixing background music into video...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr[-1500:])
        print("[JARVIS] Music mix failed — keeping the video without background music.")
        return video_path

    print(f"Video with music saved to: {output_path}")
    return output_path


register_skill(
    name="caption_color",
    triggers=[
        "caption color", "caption colour", "captions to", "make captions",
        "change caption color", "set caption color",
    ],
    handler=handle_caption_color_command,
    permission_level="safe",
)
