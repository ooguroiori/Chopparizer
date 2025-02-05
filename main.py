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
        
        try:
            data = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(url, download=False)
            )
            
            if 'entries' in data:
                entries = data['entries']
                print(f"[DEBUG] プレイリスト検出: {len(entries)}曲")
                return entries
            else:
                print("[DEBUG] 単曲を処理中")
                return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)
                    
        except Exception as e:
            print(f"[DEBUG] 処理中の情報: {data if 'data' in locals() else 'データなし'}")
            print(f"[ERROR] 情報取得エラー: {str(e)}")
            raise

    async def play_next(self, ctx):
        if len(self.queue) > 0:
            self.is_playing = True
            self.current_song = self.queue[0]  # まだキューから削除しない
            
            try:
                print(f"[DEBUG] 次の曲を再生準備中: {self.current_song['title']}")
                player = await YTDLSource.from_url(self.current_song['url'], loop=self.loop, stream=True)
                
                if isinstance(player, list):
                    first_song = player[0]
                    audio = discord.FFmpegPCMAudio(first_song['url'], **ffmpeg_options)
                else:
                    audio = player

                def after_playing(error):
                    if error:
                        print(f"[ERROR] 再生エラー: {str(error)}")
                    self.loop.create_task(self.play_next(ctx))

                ctx.voice_client.play(audio, after=after_playing)
                self.queue.popleft()  # 再生開始後にキューから削除
                
                print(f"[DEBUG] 再生開始: {self.current_song['title']}")

                if self.repeat:
                    self.queue.append(self.current_song)
            
            except Exception as e:
                print(f"[ERROR] 再生エラー: {str(e)}")
                self.queue.popleft()  # エラー時もキューから削除
                await self.play_next(ctx)
        else:
            self.is_playing = False


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
        self.play_lock = asyncio.Lock()  # 追加: 同期制御用のロック

    async def play_next(self, ctx):
        async with self.play_lock:  # ロックを使用
            if len(self.queue) > 0:
                try:
                    # 現在の再生を確実に停止
                    if ctx.voice_client and ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                        await asyncio.sleep(0.5)

                    if not ctx.voice_client:
                        return

                    self.current_song = self.queue.popleft()
                    print(f"[DEBUG] 再生準備中: {self.current_song['title']}")

                    player = await YTDLSource.from_url(self.current_song['url'], loop=self.loop, stream=True)
                    self.is_playing = True

                    if isinstance(player, list):
                        first_song = player[0]
                        audio = discord.FFmpegPCMAudio(first_song['url'], **ffmpeg_options)
                    else:
                        audio = player

                    def after_playing(error):
                        if error:
                            print(f"[ERROR] 再生エラー: {str(error)}")
                        asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.loop)

                    ctx.voice_client.play(audio, after=after_playing)
                    print(f"[DEBUG] 再生開始: {self.current_song['title']}")

                    if self.repeat:
                        self.queue.append(self.current_song)

                    await ctx.send(f'🎵 再生中: {self.current_song["title"]}')

                except Exception as e:
                    print(f"[ERROR] 再生エラー: {str(e)}")
                    await self.play_next(ctx)
            else:
                self.is_playing = False
                self.current_song = None

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

    async def process_playlist():
        result = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        if isinstance(result, list):
            print(f"\n[PLAYLIST] プレイリストを検出: {len(result)}曲")
            for i, song in enumerate(result, 1):
                song_info = {
                    'url': song.get('url') or song.get('webpage_url') or song['id'],  # 複数のフィールドをチェック
                    'title': song.get('title', f'Track {i}'),  # タイトルがない場合はTrack番号
                    'requester': ctx.author
                }
                bot.queue.append(song_info)
                print(f"[PLAYLIST] {i}. {song_info['title']}")
                
                # 最初の曲の場合かつ再生していない場合は再生開始
                if i == 1 and not bot.is_playing:
                    await bot.play_next(ctx)
            
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
                await bot.play_next(ctx)

    # プレイリスト処理を非同期で開始
    asyncio.create_task(process_playlist())

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("スキップしました")
    else:
        await ctx.send("再生中の曲がありません")

async def play_next(self, ctx):
    # スキップ処理中は重複実行を防ぐ
    if hasattr(self, 'skip_in_progress') and self.skip_in_progress:
        return

    if len(self.queue) > 0:
        try:
            self.current_song = self.queue[0]
            print(f"[DEBUG] 再生準備中: {self.current_song['title']}")

            player = await YTDLSource.from_url(self.current_song['url'], loop=self.loop, stream=True)
            
            # 再生前に現在の状態をチェック
            if ctx.voice_client and ctx.voice_client.is_playing():
                return
            
            self.is_playing = True
            if isinstance(player, list):
                first_song = player[0]
                audio = discord.FFmpegPCMAudio(first_song['url'], **ffmpeg_options)
            else:
                audio = player

            def after_playing(error):
                if error:
                    print(f"[ERROR] 再生エラー: {str(error)}")
                if not self.skip_in_progress:
                    asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.loop)

            ctx.voice_client.play(audio, after=after_playing)
            self.queue.popleft()
            
            print(f"[DEBUG] 再生開始: {self.current_song['title']}")

            if self.repeat:
                self.queue.append(self.current_song)
            
            await ctx.send(f'🎵 再生中: {self.current_song["title"]}')
            
        except Exception as e:
            print(f"[ERROR] 再生エラー: {str(e)}")
            self.queue.popleft()
    else:
        self.is_playing = False
        self.current_song = None



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