from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from collections import deque
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# YTDLのオプション設定
ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,  # エラーを無視して続行
    'logtostderr': False,
    'quiet': False,  # 進行状況を表示
    'no_warnings': False,  # 警告を表示
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,    # IPv4を強制
    'sleep-interval': 1,   # リクエスト間隔を短く
    'max-sleep-interval': 5
}


ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        print("[DEBUG] Starting from_url method")
        loop = loop or asyncio.get_event_loop()
        print(f"[DEBUG] Extracting info for URL: {url}")
        
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            if data is None:
                print("[DEBUG] データの取得に失敗しました")
                raise ValueError("動画情報を取得できませんでした")
                
            print("[DEBUG] データ取得成功")
            print(f"[DEBUG] データタイプ: {type(data)}")
            
            if 'entries' in data:
                print(f"[DEBUG] プレイリスト検出: {len(data['entries'])}曲")
                return data['entries']
            else:
                print("[DEBUG] 単曲検出")
                filename = data['url'] if stream else ytdl.prepare_filename(data)
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
                
        except Exception as e:
            print(f"[DEBUG] エラー発生: {str(e)}")
            raise



class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.queue = deque()
        self.is_playing = False
        self.is_paused = False
        self.repeat = False
        self.current_song = None

    async def play_next(self, ctx):
        if len(self.queue) > 0:
            self.is_playing = True
            self.current_song = self.queue.popleft()

            async with ctx.typing():
                player = await YTDLSource.from_url(self.current_song['url'], loop=self.loop, stream=True)
                if isinstance(player, list):
                    # プレイリストの場合は最初の曲を再生
                    first_song = player[0]
                    filename = first_song['url']
                    ctx.voice_client.play(discord.FFmpegPCMAudio(filename, **ffmpeg_options), 
                                        after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.loop))
                else:
                    # 単曲の場合
                    ctx.voice_client.play(player, 
                                        after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.loop))

            if self.repeat:
                self.queue.append(self.current_song)
            
            await ctx.send(f'再生中: {self.current_song["title"]}')
        else:
            self.is_playing = False

bot = MusicBot()

@bot.command(name='play')
async def play(ctx, url):
    if not ctx.message.author.voice:
        await ctx.send("ボイスチャンネルに接続してください！")
        return

    print(f"\n[DEBUG] Received URL: {url}")  # URLの受信を確認

    channel = ctx.message.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        print("[DEBUG] Bot connected to voice channel")
    else:
        await ctx.voice_client.move_to(channel)
        print("[DEBUG] Bot moved to voice channel")

    async with ctx.typing():
        result = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        if isinstance(result, list):
            # プレイリストの場合
            print(f"\n[DEBUG] Playlist detected! Found {len(result)} songs:")
            for song in result:
                song_info = {
                    'url': song['webpage_url'],
                    'title': song['title'],
                    'requester': ctx.author
                }
                bot.queue.append(song_info)
                print(f"[DEBUG] Added to queue: {song['title']}")
        else:
            # 単曲の場合
            print("\n[DEBUG] Single song detected!")
            song_info = {
                'url': url,
                'title': result.title,
                'requester': ctx.author
            }
            bot.queue.append(song_info)
            print(f"[DEBUG] Added to queue: {result.title}")

        await ctx.send(f'キューに追加しました: {len(result) if isinstance(result, list) else "1"} 曲')

    if not bot.is_playing:
        print("[DEBUG] Starting playback")
        await bot.play_next(ctx)

    if not bot.is_playing:
        await bot.play_next(ctx)

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("スキップしました")
        await bot.play_next(ctx)

@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        bot.is_paused = True
        await ctx.send("一時停止しました")

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client and bot.is_paused:
        ctx.voice_client.resume()
        bot.is_paused = False
        await ctx.send("再生を再開します")

@bot.command(name='queue')
async def queue(ctx):
    if len(bot.queue) == 0:
        await ctx.send("```現在のキューは空です```")
        return
    
    # Embedを作成
    embed = discord.Embed(title="🎵 再生キュー", color=0x1db954)
    
    # 現在再生中の曲を表示
    if bot.current_song:
        embed.add_field(name="再生中", value=f"🎶 {bot.current_song['title']}", inline=False)
    
    # キューの曲を表示
    queue_text = ""
    for i, song in enumerate(bot.queue, 1):
        queue_text += f"{i}. {song['title']}\n"
        # 長すぎる場合は省略
        if i >= 10:
            queue_text += f"...他 {len(bot.queue) - 10} 曲"
            break
    
    embed.add_field(name="待機中", value=queue_text if queue_text else "なし", inline=False)
    embed.set_footer(text=f"合計: {len(bot.queue)}曲")
    
    await ctx.send(embed=embed)

@bot.command(name='repeat')
async def repeat(ctx):
    bot.repeat = not bot.repeat
    await ctx.send(f"リピート: {'オン' if bot.repeat else 'オフ'}")

@bot.command(name='shuffle')
async def shuffle(ctx):
    queue_list = list(bot.queue)
    random.shuffle(queue_list)
    bot.queue = deque(queue_list)
    await ctx.send("キューをシャッフルしました")

@bot.command(name='stop')
async def stop(ctx):
    bot.queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    bot.is_playing = False
    bot.is_paused = False
    await ctx.send("再生を停止し、キューをクリアしました")

@bot.event
async def on_ready():
    print(f'ボットが起動しました: {bot.user.name}')
    print('-------------------')

bot.run(TOKEN)