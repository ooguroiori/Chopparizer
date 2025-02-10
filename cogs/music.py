# 必要なライブラリのインポート
import discord
from discord.ext import commands
import asyncio
from collections import deque
import random
from models.music_source import YTDLSource
from config.settings import FFMPEG_OPTIONS

# 音楽機能を管理するCogクラス
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot                   # Botインスタンス
        self.queue = deque()             # 再生待ちの曲キュー
        self.is_playing = False          # 再生状態
        self.is_paused = False           # 一時停止状態
        self.repeat = False              # リピート状態
        self.current_song = None         # 現在再生中の曲
        self.play_lock = asyncio.Lock()  # 同期制御用ロック
        self.repeat_queue = deque()      # リピート用のキューを追加

    # 次の曲を再生する非同期関数
    async def play_next(self, ctx):
        async with self.play_lock:  # 同期制御開始
            if len(self.queue) > 0:
                try:
                    # 現在再生中の曲を停止
                    if ctx.voice_client and ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                        await asyncio.sleep(0.5)

                    # ボイスクライアント確認
                    if not ctx.voice_client:
                        return
                    
                    # リピートモードが有効な場合、現在の曲をキューの最後に追加
                    if self.repeat and self.current_song:
                        self.queue.append(self.current_song)

                    # キューから次の曲を取得
                    self.current_song = self.queue.popleft()
                    print(f"[DEBUG] 再生準備中: {self.current_song['title']}")

                    # 音源を準備
                    player = await YTDLSource.from_url(self.current_song['url'], loop=self.bot.loop, stream=True)
                    self.is_playing = True

                    # プレイリストか単曲かを判定
                    if isinstance(player, list):
                        first_song = player[0]
                        audio = discord.FFmpegPCMAudio(first_song['url'], **FFMPEG_OPTIONS)
                    else:
                        audio = player

                    # 再生完了後のコールバック関数
                    def after_playing(error):
                        if error:
                            print(f"[ERROR] 再生エラー: {str(error)}")
                        asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

                    # 音声の再生を開始
                    ctx.voice_client.play(audio, after=after_playing)
                    print(f"[DEBUG] 再生開始: {self.current_song['title']}")

                    # リピート設定の場合はキューに追加
                    if self.repeat:
                        self.queue.append(self.current_song)

                    # 再生開始メッセージを送信
                    await ctx.send(f'🎵 再生中: {self.current_song["title"]}')

                except Exception as e:
                    print(f"[ERROR] 再生エラー: {str(e)}")
                    await self.play_next(ctx)
            else:
                self.is_playing = False
                self.current_song = None

    # 再生コマンド
    @commands.command(name='play')
    async def play(self, ctx, url):
        # ユーザーがボイスチャンネルにいるか確認
        if not ctx.message.author.voice:
            await ctx.send("ボイスチャンネルに接続してください！")
            return

        print(f"\n[PLAYLIST] URLを受信: {url}")

        # ボイスチャンネルに接続
        channel = ctx.message.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
            print("[PLAYLIST] ボイスチャンネルに接続しました")
        else:
            await ctx.voice_client.move_to(channel)

        # プレイリスト処理用の非同期関数
        async def process_playlist():
            try:
                result = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

                if result is None:
                    print(f"\n⚠️ スキップ: {url} は再生できません（ブロックまたはエラー）")
                    return  # スキップして終了

                if isinstance(result, list):
                    # プレイリストの処理
                    print(f"\n[PLAYLIST] プレイリストを検出: {len(result)}曲")
                    for i, song in enumerate(result, 1):
                        song_url = song.get('url') or song.get('webpage_url') or song.get('id')
                        if not song_url:
                            print(f"⚠️ スキップ: {song.get('title', '不明な曲')}（URL取得失敗）")
                            continue

                        song_info = {
                            'url': song_url,
                            'title': song.get('title', f'Track {i}'),
                            'requester': ctx.author
                        }
                        self.queue.append(song_info)
                        print(f"[PLAYLIST] {i}. {song_info['title']}")

                        # 最初の曲を再生
                        if i == 1 and not self.is_playing:
                            await self.play_next(ctx)

                    print(f"[PLAYLIST] 全{len(result)}曲の読み込みが完了")
                else:
                    # 単曲の処理
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

            except Exception as e:
                print(f"\n⚠️ エラー: プレイリストの処理中に問題が発生しました: {e}")

        # プレイリスト処理を非同期で開始
        asyncio.create_task(process_playlist())

    # スキップコマンド
    @commands.command(name='skip')
    async def skip(self, ctx):
        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
                await ctx.send("スキップしました")
        else:
            await ctx.send("再生中の曲がありません")

    # 一時停止コマンド
    @commands.command(name='pause')
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            self.is_paused = True
            await ctx.send("一時停止しました")

    # 再開コマンド
    @commands.command(name='resume')
    async def resume(self, ctx):
        if ctx.voice_client and self.is_paused:
            ctx.voice_client.resume()
            self.is_paused = False
            await ctx.send("再生を再開します")

    # キュー表示コマンド
    @commands.command(name='queue')
    async def queue(self, ctx):
        if len(self.queue) == 0:
            await ctx.send("```現在のキューは空です```")
            return
        
        # Embedを作成して現在のキューを表示
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

    # リピートコマンド
    @commands.command(name='repeat')
    async def repeat(self, ctx):
        self.repeat = not self.repeat
        await ctx.send(f"リピート: {'オン' if self.repeat else 'オフ'}")

    # シャッフルコマンド
    @commands.command(name='shuffle')
    async def shuffle(self, ctx):
        queue_list = list(self.queue)
        random.shuffle(queue_list)
        self.queue = deque(queue_list)
        await ctx.send("キューをシャッフルしました")

    # 停止コマンド
    @commands.command(name='stop')
    async def stop(self, ctx):
        self.queue.clear()
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        self.is_playing = False
        self.is_paused = False
        await ctx.send("再生を停止し、キューをクリアしました")
