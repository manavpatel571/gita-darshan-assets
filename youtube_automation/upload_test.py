import json
from youtube_uploader import upload_video

# Get metadata from episodes
with open(r'd:\old_laptop\startup\gita\mobile\src\data\episodes.json', 'r', encoding='utf-8') as f:
    episodes = json.load(f)
    
ep = next(e for e in episodes if e['chapter'] == 1 and e['verse'] == 1)

title = f'Bhagavad Gita Chapter 1 Verse 1 #Shorts #BhagavadGita'
desc = f"{ep['sanskrit']}\n\n{ep['dialogue'][1]['text']}\n\nDaily Shloka from the Bhagavad Gita App.\nChannel: https://www.youtube.com/channel/UCWTBK6mUpE80zm66HNHAUUw"
tags = ['BhagavadGita', 'Shorts', 'Krishna', 'Spirituality', 'Hinduism', 'DailyShloka']

upload_video('test_output.mp4', title, desc, tags, 'private')
