import os
import glob
from tools.youtube_uploader import upload_video

CODE_WORD = "blandina"
OUTPUT_DIR = "workspace/output"

def find_latest_video():
    files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def run_upload_flow():
    video_path = find_latest_video()
    if not video_path:
        print("No video found in workspace/output/.")
        return

    print(f"Found video: {video_path}")
    title = input("Enter the title for this video: ").strip()
    description = input("Enter the description (or press Enter to skip): ").strip()
    privacy = input("Privacy - private/unlisted/public [private]: ").strip().lower() or "private"

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
        print(f"Done! https://youtu.be/{video_id}")

if __name__ == "__main__":
    run_upload_flow()
