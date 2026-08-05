import json
import os
from pathlib import Path
from rich.console import Console
from video_generator import generate_video
from youtube_uploader import upload_video

console = Console()

ROOT_DIR = Path(__file__).parent
HISTORY_FILE = ROOT_DIR / "history.json"
OUTPUT_DIR = ROOT_DIR / "output"

def get_next_shloka():
    if not HISTORY_FILE.exists():
        # Start at 1.1 if no history
        return 1, 1
        
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
        
    if not history:
        return 1, 1
        
    last_entry = history[-1]
    last_ch = last_entry["chapter"]
    last_v = last_entry["verse"]
    
    # We don't have the exact number of verses per chapter here, 
    # but we can try next verse, and if it fails in generator, increment chapter.
    # For now, let's just increment verse.
    return last_ch, last_v + 1

def update_history(chapter, verse, video_id):
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
            
    history.append({
        "chapter": chapter,
        "verse": verse,
        "youtube_id": video_id
    })
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    chapter, verse = get_next_shloka()
    console.print(f"[bold green]Starting Daily Automation for {chapter}.{verse}[/bold green]")
    
    video_path = OUTPUT_DIR / f"shloka_{chapter}_{verse}.mp4"
    
    try:
        # 1. Generate Video
        metadata = generate_video(chapter, verse, str(video_path))
        
        # 2. Upload Video
        # Note: the user can change privacy to "public" after testing
        upload_response = upload_video(
            video_path=str(video_path),
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            privacy="private"
        )
        
        # 3. Save History
        video_id = upload_response["id"]
        update_history(chapter, verse, video_id)
        
        console.print("[bold green]Daily Automation Completed Successfully![/bold green]")
        
    except ValueError as e:
        # If episode not found, maybe we reached the end of the chapter
        console.print(f"[bold yellow]Verse {chapter}.{verse} failed: {e}. Trying next chapter...[/bold yellow]")
        import sys
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Automation Failed: {e}[/bold red]")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
