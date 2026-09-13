"""YouTube publisher: upload the latest render (CLI + voice skill).

CLI (interactive):   python -m skills.youtube_publisher
Voice:               "upload my latest video to youtube" (approval-gated)

Google API imports are LAZY so this skill registers — and its tests run —
even without the upload dependencies installed. If they're missing at
runtime, the handler says so instead of crashing skill discovery.
"""

import glob
import os
import re

from core.project import VideoProject
from core.skill_manager import register_skill

CODE_WORD = "blandina"
OUTPUT_DIR = "workspace/output"
LATEST_FILE = os.path.join(OUTPUT_DIR, "latest.txt")
PRIVACY_OPTIONS = ("private", "unlisted", "public")


def normalize_privacy(value):
    """Anything outside private/unlisted/public falls back to private."""
    v = (value or "").strip().lower()
    return v if v in PRIVACY_OPTIONS else "private"


def extract_title(user_input, video_path):
    """Title from 'upload it titled "Y"' / 'as Y', else prettified filename."""
    quoted = re.search(r"[\"'](.+?)[\"']", user_input or "")
    if quoted:
        return quoted.group(1).strip()
    lower = (user_input or "").lower()
    for key in (" titled ", " as "):
        if key in lower:
            title = user_input[lower.index(key) + len(key):].strip().strip("\"'")
            if title:
                return title
    base = os.path.splitext(os.path.basename(video_path or ""))[0]
    pretty = re.sub(r"output_final_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_?", "", base)
    pretty = pretty.replace("_", " ").replace("-", " ").strip()
    return pretty.title() or "Untitled JARVIS video"


def find_latest_video():
    """Newest finished render: latest.txt pointer, then output_final_*, then any mp4."""
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, encoding="utf-8") as f:
            pointed = f.read().strip()
        if pointed and os.path.exists(pointed):
            return pointed
    files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
    if not files:
        return None
    finals = [f for f in files if "output_final_" in os.path.basename(f)]
    return max(finals or files, key=os.path.getmtime)


def record_upload(video_path, video_id):
    """Stamp the matching project ticket with the YouTube URL (if found)."""
    ticket = VideoProject.find_by_output(video_path)
    if ticket is None:
        return None
    ticket.youtube_url = f"https://youtu.be/{video_id}"
    ticket.mark("published", ticket.youtube_url)
    return ticket


def run_upload_flow():
    """Interactive CLI flow: pick latest video, confirm, upload."""
    from tools.youtube_uploader import upload_video  # lazy: needs google libs

    video_path = find_latest_video()
    if not video_path:
        print("No video found in workspace/output/.")
        return

    print(f"Found video: {video_path}")
    title = input("Enter the title for this video: ").strip()
    description = input("Enter the description (or press Enter to skip): ").strip()
    privacy = normalize_privacy(
        input("Privacy - private/unlisted/public [private]: "))

    print("\n--- READY TO UPLOAD ---")
    print(f"File: {video_path}")
    print(f"Title: {title}")
    print(f"Description: {description}")
    print(f"Privacy: {privacy}")
    print("------------------------\n")

    confirm = input("Type your code word to confirm, or anything else to cancel: ").strip().lower()
    if confirm != CODE_WORD:
        print("Upload cancelled.")
        return

    video_id = upload_video(
        file_path=video_path,
        title=title,
        description=description,
        privacy_status=privacy,
    )
    if video_id:
        record_upload(video_path, video_id)
        print(f"Done! https://youtu.be/{video_id}")


def handle_youtube_publish(user_input, gemini_client=None):
    try:
        from tools.youtube_uploader import upload_video  # lazy: needs google libs
    except ImportError as e:
        return (f"I can't upload yet, Sir Gerald — the YouTube libraries are missing ({e}). "
                f"Run: pip install -r requirements.txt")

    video_path = find_latest_video()
    if not video_path:
        return ("There's no finished video to upload, Sir Gerald. "
                "Say 'make a Roblox rant about...' first.")
    title = extract_title(user_input, video_path)

    try:
        video_id = upload_video(
            file_path=video_path,
            title=title,
            description="",
            privacy_status="private",  # voice uploads stay private until you say otherwise
        )
    except SystemExit as e:
        return str(e)  # missing client_secrets.json — message already explains the fix
    except Exception as e:
        return f"The upload failed, Sir Gerald: {e}."
    if not video_id:
        return "The upload didn't go through, Sir Gerald — check the terminal output."

    record_upload(video_path, video_id)
    return (f"Published to YouTube as private, Sir Gerald: https://youtu.be/{video_id} — "
            f"titled '{title}'. Say the word and I'll make the next one.")


register_skill(
    name="youtube_publisher",
    triggers=[
        "upload to youtube", "publish to youtube", "upload my video",
        "upload the video", "publish my video", "put it on youtube",
    ],
    handler=handle_youtube_publish,
    permission_level="approval_required",
)


if __name__ == "__main__":
    run_upload_flow()
