import os
import time
import requests
from pathlib import Path
from rich.console import Console

console = Console()

def upload_to_cdn(filepath: str) -> str:
    """Uploads file to uguu.se to get a temporary public URL for Instagram."""
    console.print("[cyan]Uploading video to CDN (uguu.se)...[/cyan]")
    url = "https://uguu.se/upload.php"
    with open(filepath, "rb") as f:
        res = requests.post(url, files={"files[]": (Path(filepath).name, f, "video/mp4")})
    
    if res.status_code == 200:
        data = res.json()
        if data.get("success") and data.get("files"):
            raw_url = data["files"][0]["url"]
            console.print(f"[green]CDN Upload successful: {raw_url}[/green]")
            return raw_url
            
    console.print(f"[red]CDN Upload failed: {res.text}[/red]")
    return None

def upload_reel(video_path: str, caption: str) -> bool:
    """
    Uploads a video to Instagram Reels using the Official Meta Graph API.
    """
    access_token = os.getenv("META_ACCESS_TOKEN")
    ig_user_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    if not access_token or not ig_user_id:
        console.print("[yellow]META_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID not found in environment. Skipping Instagram upload.[/yellow]")
        return False

    console.print(f"[cyan]Initializing Instagram Reel upload via Meta Graph API...[/cyan]")
    
    # STEP 1: Upload to CDN to get public URL
    video_url = upload_to_cdn(str(video_path))
    if not video_url:
        return False
    
    # STEP 2: Initialize Instagram Upload Container
    init_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    init_payload = {
        "access_token": access_token,
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption
    }
    
    init_res = requests.post(init_url, data=init_payload).json()
    
    if "id" not in init_res:
        console.print(f"[red]Failed to initialize Instagram upload session: {init_res}[/red]")
        return False
        
    container_id = init_res["id"]
    console.print(f"[dim]Upload session started. Container ID: {container_id}[/dim]")
    
    # STEP 3: Wait for Meta servers to download and process the video
    console.print("[cyan]Waiting for Meta servers to process the video...[/cyan]")
    status_url = f"https://graph.facebook.com/v19.0/{container_id}?fields=status_code&access_token={access_token}"
    
    max_retries = 15
    ready = False
    
    for _ in range(max_retries):
        time.sleep(10)
        status_res = requests.get(status_url).json()
        status = status_res.get("status_code")
        
        console.print(f"[dim]Status: {status}[/dim]")
        
        if status == "FINISHED":
            ready = True
            break
        elif status == "ERROR":
            console.print(f"[red]Meta failed to process the video. Full response: {status_res}[/red]")
            return False
            
    if not ready:
        console.print("[red]Timed out waiting for Instagram video processing.[/red]")
        return False
        
    # STEP 4: Publish
    console.print("[cyan]Publishing Reel to Instagram...[/cyan]")
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    publish_payload = {
        "access_token": access_token,
        "creation_id": container_id
    }
    
    publish_res = requests.post(publish_url, data=publish_payload).json()
    
    if "id" in publish_res:
        console.print(f"[green]Reel published successfully! ID: {publish_res['id']}[/green]")
        return True
    else:
        console.print(f"[red]Failed to publish reel: {publish_res}[/red]")
        return False

if __name__ == "__main__":
    pass
