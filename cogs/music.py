import discord
from discord.ext import commands
import asyncio
from collections import deque
import random
from models.music_source import YTDLSource
from config.settings import FFMPEG_OPTIONS

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = deque()
        self.is_playing = False
        self.is_paused = False
        self.repeat = False
        self.current_song = None
        self.play_lock = asyncio.Lock()

    async def play_next(self, ctx):
        async with self.play_lock:
            if len(self.queue) > 0:
                try:
                    if ctx.voice_client and ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                        await asyncio.sleep(0.5)

                    if not ctx.voice_client:
                        return

                    self.current_song = self.queue.popleft()
                    print(f"[DEBUG] 再生準備中: {self.current_song['title']}")

                    player = await YTDLSource.from_url(self.current_song['url'], loop=self.bot.loop, stream=True)
                    self.is_playing = True

                    if isinstance(player, list):
                        first_song = player[0]
                        audio = discord.FFmpegPCMAudio(first_song['url'], **FFMPEG_OPTIONS)
                    else:
                        audio = player

                    def after_playing(error):
                        if error:
                            print(f"[ERROR] 再生エラー: {str(error)}")
                        asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

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

    @commands.command(name='play')
    async def play(self, ctx, url):
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
            result = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            if isinstance(result, list):
                print(f"\n[PLAYLIST] プレイリストを検出: {len(result)}曲")
                for i, song in enumerate(result, 1):
                    song_info = {
                        'url': song.get('url') or song.get('webpage_url') or song['id'],
                        'title': song.get('title', f'Track {i}'),
                        'requester': ctx.author
                    }
                    self.queue.append(song_info)
                    print(f"[PLAYLIST] {i}. {song_info['title']}")
                    
                    if i == 1 and not self.is_playing:
                        await self.play_next(ctx)
                
                print(f"[PLAYLIST] 全{len(result)}曲の読み込みが完了")
            else:
                print("\n[PLAYLIST] 単曲を検出")
                song_info = {
                    'url': url,
                    'title': result.title,
                    'requester': ctx.author
                }
                self.queue.append(song_info)
                print(f"[PLAYLIST] 追加: {result.title}")
                
                if not self.is_playing:
                    await self.play_next(ctx)

        asyncio.create_task(process_playlist())

    @commands.command(name='skip')
    async def skip(self, ctx):
        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
                await ctx.send("スキップしました")
        else:
            await ctx.send("再生中の曲がありません")

    @commands.command(name='pause')
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            self.is_paused = True
            await ctx.send("一時停止しました")

    @commands.command(name='resume')
    async def resume(self, ctx):
        if ctx.voice_client and self.is_paused:
            ctx.voice_client.resume()
            self.is_paused = False
            await ctx.send("再生を再開します")

    @commands.command(name='queue')
    async def queue(self, ctx):
        if len(self.queue) == 0:
            await ctx.send("```現在のキューは空です```")
            return
        
        embed = discord.Embed(title="🎵 再生キュー", color=0x1db954)
        
        if self.current_song:
            embed.add_field(name="再生中", value=f"🎶 {self.current_song['title']}", inline=False)
        
        queue_text = ""
        for i, song in enumerate(self.queue, 1):
            queue_text += f"{i}. {song['title']}\n"
            if i >= 10:
                queue_text += f"...他 {len(self.queue) - 10} 曲"
                break
        
        embed.add_field(name="待機中", value=queue_text if queue_text else "なし", inline=False)
        embed.set_footer(text=f"合計: {len(self.queue)}曲")
        
        await ctx.send(embed=embed)

    @commands.command(name='repeat')
    async def repeat(self, ctx):
        self.repeat = not self.repeat
        await ctx.send(f"リピート: {'オン' if self.repeat else 'オフ'}")

    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        queue_list = list(self.queue)
        random.shuffle(queue_list)
        self.queue = deque(queue_list)
        await ctx.send("キューをシャッフルしました")

    @commands.command(name='stop')
    async def stop(self, ctx):
        self.queue.clear()
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        self.is_playing = False
        self.is_paused = False
        await ctx.send("再生を停止し、キューをクリアしました")
