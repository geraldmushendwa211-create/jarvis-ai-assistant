import os
import glob
import subprocess
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from faster_whisper import WhisperModel
import imageio_ffmpeg
from core.skill_manager import register_skill

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
FOOTAGE_DIR = os.path.join(WORKSPACE_DIR, "footage")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920

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


def find_footage_clip():
    """Find the first video file in workspace/footage."""
    if not os.path.exists(FOOTAGE_DIR):
        return None
    video_files = glob.glob(os.path.join(FOOTAGE_DIR, "*.mp4"))
    if not video_files:
        return None
    return video_files[0]


def resize_to_vertical(clip):
    """Crop/resize a clip to fill a 1080x1920 vertical frame."""
    clip_ratio = clip.w / clip.h
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT

    if clip_ratio > target_ratio:
        clip = clip.resized(height=TARGET_HEIGHT)
        clip = clip.cropped(x_center=clip.w / 2, width=TARGET_WIDTH)
    else:
        clip = clip.resized(width=TARGET_WIDTH)
        clip = clip.cropped(y_center=clip.h / 2, height=TARGET_HEIGHT)

    return clip


def transcribe_words(voiceover_path):
    """Transcribe voiceover_path with faster-whisper, return a list of word timings."""
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(voiceover_path, word_timestamps=True)
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({"word": word.word.strip(), "start": word.start, "end": word.end})
    return words


def generate_captions(voiceover_path, ass_path=None, color=None):
    """
    Transcribe the voiceover and write a stylized word-by-word ASS caption file.
    """
    if ass_path is None:
        ass_path = os.path.join(OUTPUT_DIR, "captions.ass")

    if color is None:
        color = CURRENT_CAPTION_COLOR

    primary_colour = CAPTION_COLORS.get(color, CAPTION_COLORS["gold"])

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
        for w in words:
            start = format_time(w["start"])
            end = format_time(w["end"])
            text = w["word"].upper()
            line = (
                f"Dialogue: 0,{start},{end},Caption,,0,0,0,,"
                f"{{\\fscx60\\fscy60\\t(0,90,\\fscx100\\fscy100)}}{text}\n"
            )
            f.write(line)

    print(f"Styled captions ({color}) saved to: {ass_path}")
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


def trim_dead_space(voiceover_path, output_filename=None, max_gap=0.4, padding=0.05):
    """
    Removes excess silence between spoken words in the voiceover.
    """
    from pydub import AudioSegment
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

    words = transcribe_words(voiceover_path)
    if not words:
        print("No words detected — skipping trim.")
        return voiceover_path

    audio = AudioSegment.from_file(voiceover_path)
    total_ms = len(audio)

    keep_segments = []
    cursor = 0.0
    for i in range(len(words) - 1):
        gap_start = words[i]["end"]
        gap_end = words[i + 1]["start"]
        gap = gap_end - gap_start
        if gap > max_gap:
            keep_segments.append((cursor, gap_start + padding))
            cursor = gap_end - padding
    keep_segments.append((cursor, total_ms / 1000))

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
    return output_path


def create_short(voiceover_path, output_filename="output_short.mp4", footage_path=None):
    """
    Stage A: assembles a vertical short by trimming/looping footage to match
    the voiceover length, cropping it to 1080x1920, and attaching the audio.
    footage_path lets a caller (like roblox_creator.py) specify exactly which
    clip to use; if not given, falls back to find_footage_clip() as before.
    """
    if footage_path is None:
        footage_path = find_footage_clip()
    if not footage_path:
        print("No footage found in workspace/footage. Add a video clip first.")
        return None

    print(f"Using footage: {footage_path}")

    voiceover = AudioFileClip(voiceover_path)
    voice_duration = voiceover.duration
    print(f"Voiceover duration: {voice_duration:.2f}s")

    footage = VideoFileClip(footage_path)

    if footage.duration < voice_duration:
        loops_needed = int(voice_duration // footage.duration) + 1
        footage = concatenate_videoclips([footage] * loops_needed)

    footage = footage.subclipped(0, voice_duration)
    footage = resize_to_vertical(footage)
    footage = footage.with_audio(voiceover)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    footage.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

    print(f"Video saved to: {output_path}")
    return output_path


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
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if music_path is None:
        music_path = os.path.join(WORKSPACE_DIR, "music", "background_music.mp3")

    if not os.path.exists(music_path):
        print(f"No background music found at {music_path}")
        return None

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
        return None

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