import json
import os
from pathlib import Path
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip, concatenate_audioclips, ImageClip
import moviepy.video.fx.all as vfx
from rich.console import Console
from image_generator import generate_segment_image

console = Console()

# Try to use relative paths for GitHub Actions, otherwise fallback to local dev path
ROOT_DIR = Path(__file__).parent
LOCAL_ASSETS = ROOT_DIR / "assets"

if LOCAL_ASSETS.exists():
    ASSETS_CHARACTERS = LOCAL_ASSETS / "characters"
    ASSETS_AUDIO_LOCAL = LOCAL_ASSETS / "audio"
    EPISODES_PATH = LOCAL_ASSETS / "episodes.json"
else:
    GITA_ROOT = Path(r"d:\old_laptop\startup\gita")
    ASSETS_CHARACTERS = GITA_ROOT / "mobile/assets/characters"
    ASSETS_AUDIO_LOCAL = GITA_ROOT / "mobile/assets/audio"
    EPISODES_PATH = GITA_ROOT / "mobile/src/data/episodes.json"
    
ASSETS_AUDIO_CDN = ASSETS_AUDIO_LOCAL # For backward compatibility

def get_character_video(speaker, label=None):
    """Map speaker and label from episodes.json to the correct character animation."""
    if label == "कथावाचक":
        return ASSETS_CHARACTERS / "vakta.mp4"
        
    mapping = {
        "धृतराष्ट्र": "sanjaya_speak_stage.mp4",
        "संजय": "sanjaya_speak_stage.mp4",
        "अर्जुन": "arjuna_speak_stage.mp4",
        "श्री भगवान्": "krishna_speak_a_stage.mp4",
        "narrator": "vakta.mp4",
        "dhritarashtra": "sanjaya_speak_stage.mp4",
        "sanjaya": "sanjaya_speak_stage.mp4",
        "arjuna": "arjuna_speak_stage.mp4",
        "krishna": "krishna_speak_a_stage.mp4"
    }
    
    if label and label in mapping:
        video_name = mapping[label]
    else:
        video_name = mapping.get(speaker.lower(), "sanjaya_speak_stage.mp4")
        
    return ASSETS_CHARACTERS / video_name

def generate_video(chapter: int, verse: int, output_path: str) -> dict:
    console.print(f"[cyan]Generating Video for Chapter {chapter}, Verse {verse}...[/cyan]")
    # Read episodes data
    with open(EPISODES_PATH, "r", encoding="utf-8") as f:
        episodes = json.load(f)
    
    episode = next((e for e in episodes if e["chapter"] == chapter and e["verse"] == verse), None)
    if not episode:
        raise ValueError(f"Episode {chapter}.{verse} not found in database.")
        
    # Resolve Audio Path
    audio_dir_name = f"{chapter}_{verse}"
    audio_dir = ASSETS_AUDIO_LOCAL / audio_dir_name
    if not audio_dir.exists():
        audio_dir = ASSETS_AUDIO_CDN / audio_dir_name
        
    if audio_dir.exists():
        # Prevent duplicates by picking only one file per prefix (00, 01, 02)
        # Prefer narrator if multiple exist
        audio_files = []
        for prefix in ["00_", "01_", "02_", "03_"]:
            files = list(audio_dir.glob(f"{prefix}*.mp3"))
            if files:
                narrator_file = next((f for f in files if "narrator" in f.name.lower()), None)
                audio_files.append(narrator_file if narrator_file else files[0])
                
        if not audio_files:
            raise FileNotFoundError(f"Audio files not found in {audio_dir}")
            
    console.print(f"[dim]  Audio sourced from: {audio_dir}[/dim]")
        
    # Build Main Audio Track
    from moviepy.editor import CompositeAudioClip
    from moviepy.audio.fx.all import volumex, audio_loop
    
    audio_clips = [AudioFileClip(str(p)) for p in audio_files]
    speech_audio = concatenate_audioclips(audio_clips)
    
    # Add Background Music (BGM)
    bgm_path = ASSETS_AUDIO_LOCAL / "bgm_chariot_morning.mp3"
    if bgm_path.exists():
        bgm_clip = AudioFileClip(str(bgm_path))
        # Loop BGM to match speech duration and lower volume
        bgm_clip = audio_loop(bgm_clip, duration=speech_audio.duration)
        bgm_clip = volumex(bgm_clip, 0.08) # 8% volume
        final_audio = CompositeAudioClip([speech_audio, bgm_clip])
    else:
        final_audio = speech_audio
    
    # Video setup (9:16 aspect ratio: 1080x1920)
    width, height = 1080, 1920
    
    # Character-specific background selection with slow Ken Burns zoom
    bg_root = LOCAL_ASSETS / "backgrounds" if LOCAL_ASSETS.exists() else Path(__file__).parent / "assets" / "backgrounds"

    def get_character_bg_folder(ep):
        """Return background folder based on main speaker of this verse."""
        speakers = [d.get("speaker", "").lower() for d in ep.get("subtitles", [])]
        for s in speakers:
            if "krishna" in s or "bhagavan" in s or "lord" in s:
                return bg_root / "krishna"
            if "arjuna" in s:
                return bg_root / "arjuna"
        return bg_root / "sanjaya"  # default Dhritarashtra/Sanjaya

    def make_kenburns_bg(image_path, duration, w, h):
        """Slowly zoom into the background for a cinematic feel."""
        import numpy as np
        from PIL import Image as PILImage
        src = PILImage.open(image_path).convert("RGB")
        src_w, src_h = src.size

        fps = 24
        total_frames = int(duration * fps)
        zoom_start, zoom_end = 1.0, 1.08  # subtle 8% zoom over the whole clip

        frames = []
        for i in range(total_frames):
            t = i / max(total_frames - 1, 1)
            scale = zoom_start + (zoom_end - zoom_start) * t
            new_w = int(src_w / scale)
            new_h = int(src_h / scale)
            x_off = (src_w - new_w) // 2
            y_off = (src_h - new_h) // 2
            cropped = src.crop((x_off, y_off, x_off + new_w, y_off + new_h))
            resized = cropped.resize((w, h), PILImage.Resampling.LANCZOS)
            frames.append(np.array(resized))

        def make_frame(t):
            idx = min(int(t * fps), total_frames - 1)
            return frames[idx]

        return ImageClip(make_frame, duration=duration, ismask=False)

    try:
        char_bg_dir = get_character_bg_folder(episode)
        bg_images = sorted(char_bg_dir.glob("*.png")) if char_bg_dir.exists() else []
        if not bg_images:
            # Fallback to any generic background
            bg_images = sorted(bg_root.glob("*.png"))

        if bg_images:
            chosen_bg = bg_images[(verse - 1) % len(bg_images)]
            console.print(f"[green]  Using background: {chosen_bg.parent.name}/{chosen_bg.name}[/green]")
            ai_bg = make_kenburns_bg(str(chosen_bg), final_audio.duration, width, height)
        else:
            raise FileNotFoundError("No backgrounds found")

    except Exception as e:
        console.print(f"[yellow]Failed to load background: {e}[/yellow]")
        # Rich warm gradient fallback (golden/amber tones)
        from PIL import Image as PILImage, ImageDraw
        img = PILImage.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            r = int(80 + (20 - 80) * ratio)
            g = int(40 + (10 - 40) * ratio)
            b = int(10 + (5 - 10) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        import numpy as np
        ai_bg = ImageClip(np.array(img)).set_duration(final_audio.duration)

    # We apply a slight vignette/darkening to the AI background so text pops
    dark_overlay = ColorClip(size=(width, height), color=(0, 0, 0)).set_duration(final_audio.duration).set_opacity(0.35)

    
    # Text Overlays Helper (using PIL instead of ImageMagick for robust text rendering)
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        def create_cinematic_text_image(text, font_size, primary_color, max_width, has_shadow=True):
            img = Image.new('RGBA', (max_width, 800), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            try:
                # Check if we have our local font (for GitHub Actions / Cross-platform)
                local_font_path = LOCAL_ASSETS / "font.ttf"
                if local_font_path.exists():
                    font = ImageFont.truetype(str(local_font_path), font_size)
                else:
                    # Fallback to Windows Nirmala UI
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\Nirmala.ttc", font_size)
            except IOError:
                font = ImageFont.load_default()
            
            lines = []
            for paragraph in text.split('\n'):
                words = paragraph.split(' ')
                current_line = []
                for word in words:
                    current_line.append(word)
                    bbox = draw.textbbox((0, 0), ' '.join(current_line), font=font)
                    if bbox[2] - bbox[0] > (max_width - 80): # padding
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                lines.append(' '.join(current_line))
            
            # Calculate total height to draw ancient page box
            total_height = 40 # top and bottom padding
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                total_height += (bbox[3] - bbox[1]) + 15
                
            # Draw ancient page background (parchment color)
            draw.rounded_rectangle([0, 0, max_width, total_height], radius=15, fill=(245, 222, 179, 210), outline=(139, 69, 19, 255), width=3)
            
            y_text = 20 # Add top padding
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                x_pos = (max_width - width) / 2
                
                # Draw subtle drop shadow/outline for cinematic feel
                if has_shadow:
                    shadow_color = (0, 0, 0, 80)
                    draw.text((x_pos + 2, y_text + 2), line, font=font, fill=shadow_color)
                    
                draw.text((x_pos, y_text), line, font=font, fill=primary_color)
                y_text += height + 15
                
            img = img.crop((0, 0, max_width, y_text + 20))
            return np.array(img)

        # Upper Shloka text (constant background)
        sanskrit_text = episode["sanskrit"].replace("।", "।\n").replace("।।", "।।\n")
        ink_color = (62, 39, 35, 255) # Dark Brown/Black
        sans_img = create_cinematic_text_image(sanskrit_text, 55, ink_color, 900)
        txt_clip_sanskrit = ImageClip(sans_img).set_position(('center', 150)).set_duration(final_audio.duration)
        
        # Build character clips and lower subtitles dynamically
        from moviepy.video.fx.all import mask_color
        
        fg_clips = []
        lower_txt_clips = []
        
        for sub in episode.get("subtitles", []):
            start_t = sub["startMs"] / 1000.0
            end_t = sub["endMs"] / 1000.0
            duration = end_t - start_t
            
            # Character Clip
            speaker = sub.get("speaker", "narrator")
            label = sub.get("label", "")
            char_video_path = get_character_video(speaker, label)
            
            char_clip = VideoFileClip(str(char_video_path)).loop(duration=duration)
            
            # Remove beige background (threshold of 35 covers both Sanjaya [245,215,169] and Narrator [248,219,170])
            char_clip = mask_color(char_clip, color=[245, 215, 169], thr=35, s=5)
            
            # Resize and center
            char_clip = char_clip.resize(width=width)
            if char_clip.h > height:
                char_clip = char_clip.crop(y_center=char_clip.h/2, height=height)
                
            char_clip = char_clip.set_position("center").set_start(start_t)
            fg_clips.append(char_clip)
            
            # Subtitle Clip
            sub_text = sub["text"]
            if sub["kind"] == "sanskrit":
                sub_text = sub_text.replace("।", "।\n").replace("।।", "।।\n")
            sub_img = create_cinematic_text_image(sub_text, 40, ink_color, 900)
            txt_clip = ImageClip(sub_img).set_position(('center', 1450)).set_start(start_t).set_duration(duration)
            lower_txt_clips.append(txt_clip)
            
        final_video = CompositeVideoClip([
            ai_bg, 
            dark_overlay, 
            txt_clip_sanskrit,
            *fg_clips,
            *lower_txt_clips
        ])
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Custom text/character rendering failed ({e}).[/yellow]")
        raise e

    final_video = final_video.set_audio(final_audio)

    console.print("[cyan]Writing final video file...[/cyan]")
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    
    console.print(f"[green]Video saved successfully to {output_path}[/green]")
    
    return {
        "title": f"Bhagavad Gita Chapter {chapter} Verse {verse} #Shorts #BhagavadGita",
        "description": f"{episode['sanskrit']}\n\n{episode['dialogue'][1]['text'] if len(episode['dialogue']) > 1 else ''}\n\nDaily Shloka from the Bhagavad Gita App.\nChannel: https://www.youtube.com/channel/UCWTBK6mUpE80zm66HNHAUUw\n\nDownload the full app to listen to all verses:\nhttps://play.google.com/store/apps/details?id=com.gitadarshan.app&pcampaignid=web_share",
        "tags": ["BhagavadGita", "Shorts", "Krishna", "Spirituality", "Hinduism", "DailyShloka"]
    }

if __name__ == "__main__":
    generate_video(1, 1, str(Path(__file__).parent / "test_output.mp4"))
