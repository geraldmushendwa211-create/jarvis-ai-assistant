"""Project status reporter: "JARVIS, what have you made?".

Scans the workspace and summarizes recent videos, scripts, and ideas —
no AI call needed, so it answers instantly. Also demonstrates the simple
one-argument skill handler signature: ``(user_input)``.
"""

import os
from datetime import datetime
from core.skill_manager import register_skill

WORKSPACE_DIR = "workspace"
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output")
SCRIPTS_DIR = os.path.join(WORKSPACE_DIR, "scripts")
AUDIO_DIR = os.path.join(WORKSPACE_DIR, "audio")
LATEST_FILE = os.path.join(OUTPUT_DIR, "latest.txt")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm")


def _newest(paths):
    if not paths:
        return None
    return max(paths, key=os.path.getmtime)


def _describe(path):
    name = os.path.basename(path)
    when = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%b %d at %H:%M")
    return f"{name} ({when})"


def gather_status():
    """Collect workspace stats. Returns a dict (easy to test, easy to speak)."""
    videos, scripts, ideas, voiceovers = [], [], [], []
    if os.path.isdir(OUTPUT_DIR):
        videos = [
            os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        ]
    if os.path.isdir(SCRIPTS_DIR):
        for f in os.listdir(SCRIPTS_DIR):
            if f.startswith("ideas_") and f.endswith(".txt"):
                ideas.append(os.path.join(SCRIPTS_DIR, f))
            elif f.startswith("script_") and f.endswith(".txt"):
                scripts.append(os.path.join(SCRIPTS_DIR, f))
    if os.path.isdir(AUDIO_DIR):
        voiceovers = [
            os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR)
            if f.lower().endswith((".mp3", ".wav"))
        ]
    latest = None
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, encoding="utf-8") as f:
            latest = f.read().strip() or None
    return {
        "videos": videos,
        "scripts": scripts,
        "ideas": ideas,
        "voiceovers": voiceovers,
        "latest": latest if latest and os.path.exists(latest) else _newest(videos),
    }


def handle_project_status(user_input):
    status = gather_status()
    parts = []
    n_videos = len(status["videos"])
    if n_videos == 0:
        parts.append("no finished videos yet")
    elif n_videos == 1:
        parts.append("1 finished video")
    else:
        parts.append(f"{n_videos} finished videos")
    if status["scripts"]:
        parts.append(f"{len(status['scripts'])} scripts")
    if status["ideas"]:
        parts.append(f"{len(status['ideas'])} idea lists")
    if status["voiceovers"]:
        parts.append(f"{len(status['voiceovers'])} voiceovers")

    summary = ", ".join(parts)
    if status["latest"]:
        return (
            f"So far I've produced {summary}, Sir Gerald. "
            f"The newest video is {_describe(status['latest'])}."
        )
    if n_videos == 0 and not status["scripts"]:
        return (
            "Nothing yet, Sir Gerald — the workspace is empty. "
            "Say 'make a Roblox rant about...' and I'll get to work."
        )
    return f"So far I've produced {summary}, Sir Gerald."


register_skill(
    name="project_status",
    triggers=[
        "what have you made", "what did you make", "show my videos",
        "my videos", "project status", "jarvis status", "what have you created",
    ],
    handler=handle_project_status,
    permission_level="safe",
)
