import os
import json
from pathlib import Path
from rich.console import Console
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

console = Console()

# We expect credentials in the current directory
CREDENTIALS_DIR = Path(__file__).parent / "credentials"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"
YOUTUBE_CATEGORY_ID = "27"  # Education

def get_authenticated_service():
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            console.print("[cyan]🔄 Refreshing YouTube token...[/cyan]")
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_FILE.exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRET_FILE}. Please download OAuth client secrets from Google Cloud Console."
                )
            
            console.print("[cyan]🔑 Starting YouTube OAuth flow...[/cyan]")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        console.print("[green]✓ YouTube token saved[/green]")
    
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path: str, title: str, description: str, tags: list, privacy: str = "private") -> dict:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    youtube = get_authenticated_service()
    
    console.print(f"[cyan]📤 Uploading {video_path.name} to YouTube...[/cyan]")
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            console.print(f"  ⬆ Upload progress: {progress}%")
            
    video_id = response["id"]
    console.print(f"[green]✓ Upload complete! URL: https://youtube.com/shorts/{video_id}[/green]")
    return response

if __name__ == "__main__":
    pass
