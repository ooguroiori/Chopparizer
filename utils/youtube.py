# YouTube-DLライブラリをインポート（yt-dlpは新しいフォーク版）
import yt_dlp as youtube_dl

# 設定ファイルからYouTubeダウンロードのオプションをインポート
from config.settings import YTDL_OPTIONS

# YouTubeダウンローダーのインスタンスを作成
# このインスタンスを使って動画/音声の情報取得やダウンロードを行う
ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)
