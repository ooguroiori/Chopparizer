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
    'format': 'bestaudio',  # 'best'を削除してaudioのみに
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


ffmpeg_options = {
    'options': '-vn -threads 4 -preset ultrafast -tune zerolatency'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        tasks = []
        
        async def extract_info():
            return await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        data = await extract_info()
        
        if 'entries' in data:
            first_song = data['entries'][0]
            return cls(discord.FFmpegPCMAudio(first_song['url'], **ffmpeg_options), data=first_song)
        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)


class MusicBot(commands.Bot):
    def __init__(self):
        # 既存のコードに追加
        self.song_cache = {}  # URLをキーとしたキャッシュ
        
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.queue = deque()
        self.is_playing = False
        self.is_paused = False
        self.repeat = False
        self.current_song = None

    async def get_song_info(self, url):
        if url in self.song_cache:
            return self.song_cache[url]
        # 新規取得の場合
        info = await YTDLSource.from_url(url, loop=self.loop)
        self.song_cache[url] = info
        return info
    
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

    print(f"\n[PLAYLIST] URLを受信: {url}")

    channel = ctx.message.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        print("[PLAYLIST] ボイスチャンネルに接続しました")
    else:
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        result = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        if isinstance(result, list):
            print(f"\n[PLAYLIST] プレイリストを検出: {len(result)}曲")
            for i, song in enumerate(result, 1):
                song_info = {
                    'url': song['webpage_url'],
                    'title': song['title'],
                    'requester': ctx.author
                }
                bot.queue.append(song_info)
                print(f"[PLAYLIST] {i}. {song['title']}")
            
            print(f"[PLAYLIST] 全{len(result)}曲の読み込みが完了")
        else:
            print("\n[PLAYLIST] 単曲を検出")
            song_info = {
                'url': url,
                'title': result.title,
                'requester': ctx.author
            }
            bot.queue.append(song_info)
            print(f"[PLAYLIST] 追加: {result.title}")

    if not bot.is_playing:
        print("[PLAYLIST] 再生を開始します")
        await bot.play_next(ctx)


@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client:
        # 現在の再生を停止
        ctx.voice_client.stop()
        
        # 少し待機して確実に停止させる
        await asyncio.sleep(0.5)
        
        # 次の曲を再生
        await bot.play_next(ctx)
        await ctx.send("スキップしました")
    else:
        await ctx.send("再生中の曲がありません")


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