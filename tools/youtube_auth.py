import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "youtube_token.json"


def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Silently refresh expired tokens instead of forcing the browser
    # dance every time. Falls through to full auth if refresh fails.
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[youtube_auth] Token refresh failed ({e}) — re-authorizing.")
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(CLIENT_SECRETS_FILE):
            raise SystemExit(
                "[youtube_auth] client_secrets.json not found. Follow docs/SETUP.md "
                "('YouTube upload setup') to create OAuth credentials first."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


if __name__ == "__main__":
    youtube = get_authenticated_service()
    response = youtube.channels().list(part="snippet", mine=True).execute()
    channel_name = response["items"][0]["snippet"]["title"]
    print(f"Successfully authenticated! Connected to channel: {channel_name}")
