# 環境変数を読み込むためのライブラリをインポート
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()

# Discordボットのトークンを環境変数から取得
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# YouTube-DL用の詳細設定
YTDL_OPTIONS = {
    'format': 'bestaudio/best',      # 最高品質の音声を優先
    'extractaudio': True,            # 音声の抽出を有効化
    'audioformat': 'mp3',            # MP3形式で出力
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',  # 出力ファイル名の形式
    'restrictfilenames': True,       # ファイル名を安全に制限
    'noplaylist': False,             # プレイリストの処理を許可
    'nocheckcertificate': True,      # 証明書チェックをスキップ
    'ignoreerrors': False,           # エラーを表示（デバッグ用）
    'logtostderr': False,            # 標準エラー出力にログを出力
    'quiet': False,                  # 詳細なログを表示
    'no_warnings': False,            # 警告メッセージを表示
    'default_search': 'auto',        # 検索モードを自動に設定
    'source_address': '0.0.0.0',     # 送信元アドレスを設定
    'force-ipv4': True,              # IPv4を強制使用
    'geo_bypass': True,              # 地域制限をバイパス
    'geo_bypass_country': 'JP',      # 日本からのアクセスとして処理
    'verbose': True,                 # 詳細な情報を表示
    'extract_flat': True,            # フラット抽出を有効化
    'socket_timeout': 30,            # ソケットタイムアウトを30秒に設定
    'retries': 10,                   # 再試行回数を10回に設定
    'fragment_retries': 10,          # フラグメント再試行も10回に設定
    'hls_prefer_native': True        # ネイティブHLSプレーヤーを優先
}

# FFmpeg用の音声処理オプション
FFMPEG_OPTIONS = {
    'options': '-vn -threads 4 -preset ultrafast -tune zerolatency'
    # -vn: 映像を無効化
    # -threads 4: 4スレッドで処理
    # -preset ultrafast: 最速の処理速度を優先
    # -tune zerolatency: 低遅延モードを有効化
}
