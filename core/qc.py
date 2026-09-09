"""Quality control: verify a render without heavy dependencies.

Probing parses `ffmpeg -i` output (imageio-ffmpeg ships ffmpeg but no
ffprobe). parse_ffmpeg_info() is pure and unit-tested; probe() and
check_video() need the bundled ffmpeg binary at RUNTIME only — this module
imports fine anywhere.
"""

import os
import re
import subprocess

DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")
RESOLUTION_RE = re.compile(r"Stream.*Video:.*?,\s*(\d{2,5})x(\d{2,5})\b")
AUDIO_RE = re.compile(r"Stream.*Audio:")


def parse_ffmpeg_info(stderr_text):
    """ffmpeg -i stderr -> {duration, width, height, has_audio, has_video}."""
    info = {"duration": 0.0, "width": 0, "height": 0,
            "has_audio": False, "has_video": False}
    text = stderr_text or ""
    match = DURATION_RE.search(text)
    if match:
        info["duration"] = (int(match.group(1)) * 3600
                            + int(match.group(2)) * 60
                            + float(match.group(3)))
    match = RESOLUTION_RE.search(text)
    if match:
        info["has_video"] = True
        info["width"] = int(match.group(1))
        info["height"] = int(match.group(2))
    info["has_audio"] = AUDIO_RE.search(text) is not None
    return info


def probe(video_path):
    """Return parse_ffmpeg_info() for a real file. Raises on ffmpeg failure."""
    import imageio_ffmpeg  # lazy: keeps this module importable without video deps
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([exe, "-hide_banner", "-i", video_path],
                          capture_output=True, text=True)
    return parse_ffmpeg_info(proc.stderr)


def check_video(video_path, expect_w, expect_h, min_duration=1.0, ass_path=None):
    """Run the QC checklist. Returns {"passed": bool, "checks": [...]}."""
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    if not os.path.exists(video_path):
        add("file exists", False, str(video_path))
        return {"passed": False, "checks": checks}
    add("file exists", True)
    add("non-empty file", os.path.getsize(video_path) > 0)
    try:
        info = probe(video_path)
    except Exception as e:
        add("probe", False, str(e))
        return {"passed": False, "checks": checks}
    add("readable streams", info["width"] > 0,
        f"{info['width']}x{info['height']}")
    add("resolution", info["width"] == expect_w and info["height"] == expect_h,
        f"got {info['width']}x{info['height']}, want {expect_w}x{expect_h}")
    add("duration", info["duration"] >= min_duration,
        f"{info['duration']:.1f}s")
    add("has audio", info["has_audio"])
    if ass_path is not None:
        add("captions file", os.path.exists(ass_path), str(ass_path))
    return {"passed": all(c["ok"] for c in checks), "checks": checks}


def failed_names(qc_result):
    return [c["name"] for c in qc_result.get("checks", []) if not c["ok"]]
