"""Thumbnail generator: frame grab + bold title card (1280x720 JPEG).

Needs pillow + imageio-ffmpeg (both in requirements.txt). Callers MUST import
this module lazily and skip gracefully when it's unavailable:

    try:
        from core.thumbnail import make_thumbnail
        ...
    except Exception as e:
        print(f"Thumbnail skipped ({e})")
"""

import os
import subprocess
import textwrap

from core.qc import probe  # stdlib-safe: core.qc only needs ffmpeg at runtime
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\ariblk.ttf",   # Arial Black (Windows)
    r"C:\Windows\Fonts\arialbd.ttf",  # Arial Bold fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def _font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except TypeError:
        return ImageFont.load_default()


def extract_frame(video_path, out_png, at_ratio=0.3):
    info = probe(video_path)
    t = max(0.5, (info["duration"] or 5) * at_ratio)
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-ss", f"{t:.2f}",
         "-i", video_path, "-frames:v", "1", out_png],
        capture_output=True, check=True,
    )
    return out_png


def make_thumbnail(video_path, title_text, output_path):
    """Build a 1280x720 thumbnail from a video frame + title. Returns path."""
    frame_png = output_path + ".frame.png"
    extract_frame(video_path, frame_png)
    try:
        img = Image.open(frame_png).convert("RGB")
        # Cover-crop to 16:9.
        scale = max(W / img.width, H / img.height)
        img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
        left, top = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((left, top, left + W, top + H))
        img = img.filter(ImageFilter.GaussianBlur(1))

        draw = ImageDraw.Draw(img, "RGBA")
        draw.rectangle([0, H // 2, W, H], fill=(0, 0, 0, 140))  # text zone

        lines = textwrap.wrap((title_text or "New video").upper(), width=18)[:3]
        font = _font(92 if len(lines) < 3 else 76)
        y = H - 40 - len(lines) * 100
        for line in lines:
            draw.text((W // 2, y), line, font=font, anchor="ma",
                      fill="white", stroke_width=3, stroke_fill="black")
            y += 100
        img.save(output_path, quality=88)
    finally:
        try:
            os.remove(frame_png)
        except OSError:
            pass
    return output_path
