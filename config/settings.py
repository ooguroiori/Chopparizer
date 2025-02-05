from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

YTDL_OPTIONS = {
    'format': 'bestaudio',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',
    'force-ipv4': True,
    'buffer-size': 32768,
    'concurrent-fragments': 5,
    'postprocessor-args': ['-threads', '4'],
    'prefer-insecure': True,
    'no-check-formats': True
}

FFMPEG_OPTIONS = {
    'options': '-vn -threads 4 -preset ultrafast -tune zerolatency'
}
