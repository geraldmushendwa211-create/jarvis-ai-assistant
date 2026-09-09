import os
from googleapiclient.http import MediaFileUpload
from tools.youtube_auth import get_authenticated_service

def upload_video(file_path, title, description="", tags=None, privacy_status="private"):
    if not os.path.exists(file_path):
        print(f"Error: file not found at {file_path}")
        return None

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": privacy_status,  # "private", "unlisted", or "public"
        },
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("Uploading...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print(f"Upload complete! Video ID: {response['id']}")
    print(f"URL: https://youtu.be/{response['id']}")
    return response["id"]

if __name__ == "__main__":
    upload_video(
        file_path="workspace/output/output_with_captions.mp4",
        title="Test Upload from JARVIS",
        description="This is a test upload via the YouTube Data API.",
        tags=["test"],
        privacy_status="private",
    )
