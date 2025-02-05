# 必要なライブラリをインポート
import discord
import asyncio
from config.settings import FFMPEG_OPTIONS
from utils.youtube import ytdl

# YouTube音源を処理するためのクラス
class YTDLSource(discord.PCMVolumeTransformer):
    # 音源の初期化処理
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')  # 曲のタイトル
        self.url = data.get('url')      # 音源のURL

    # URLから音源情報を取得するクラスメソッド
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        # イベントループの取得
        loop = loop or asyncio.get_event_loop()
        
        try:
            # 非同期でYouTube情報を取得
            data = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(url, download=False)
            )
            
            # プレイリストかどうかを判定
            if 'entries' in data:
                entries = data['entries']
                print(f"[DEBUG] プレイリスト検出: {len(entries)}曲")
                return entries
            else:
                # 単曲の場合の処理
                print("[DEBUG] 単曲を処理中")
                return cls(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), data=data)
                    
        except Exception as e:
            # エラー情報の出力
            print(f"[DEBUG] 処理中の情報: {data if 'data' in locals() else 'データなし'}")
            print(f"[ERROR] 情報取得エラー: {str(e)}")
            raise
