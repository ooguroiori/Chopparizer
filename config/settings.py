# 環境変数を読み込むためのライブラリをインポート
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()

# Discordボットのトークンを環境変数から取得
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
NAME = os.getenv('USER_NAME')
PASSWORD = os.getenv('USER_PASSWORD')
# COOKIE = os.getenv('YOUTUBE_COOKIES')

# YouTube-DL用の詳細設定
YTDL_OPTIONS = {
    # 認証関連
    'username': NAME,                   # ユーザー名
    'password': PASSWORD,               # パスワード
    'cookiefile': 'youtube.cookies',    # クッキーファイルの使用

    # 基本設定
    'format': 'bestaudio',              # 最高音質のオーディオを選択
    'extractaudio': True,               # 音声のみを抽出
    'audioformat': 'mp3',               # MP3形式で出力
    'outtmpl': '%(title)s.%(ext)s',    # 出力ファイル名のテンプレート

    # 地域とネットワーク設定
    'geo_bypass': True,                 # 地域制限をバイパス
    'geo_bypass_country': 'JP',         # 日本のIPをシミュレート
    'geo_bypass_ip_block': '203.104.0.0/16',  # 日本のIPレンジ
    'proxy': 'socks5://127.0.0.1:40000',# 必要に応じてプロキシを設定可能
    'force-ipv4': True,                 # IPv4の使用を強制
    'source_address': '0.0.0.0',        # 接続元IPアドレス
    
    'restrictfilenames': True,          # ファイル名を安全な文字のみに制限
    'noplaylist': False,                # プレイリストの処理を許可
    'nocheckcertificate': True,         # SSL証明書チェックを無効化
    'ignoreerrors': True,               # エラーを無視して続行
    'logtostderr': False,               # 標準エラー出力へのログ出力を無効化
    'quiet': True,                      # 詳細な出力を抑制
    'no_warnings': True,                # 警告メッセージを抑制
    'default_search': 'auto',           # 検索モードを自動に設定
    'extract_flat': 'in_playlist',      # プレイリスト展開モード
    'buffer-size': 32768,               # バッファサイズを32KBに設定
    'concurrent-fragments': 5,          # 同時ダウンロードの最大数
    'postprocessor-args': ['-threads', '4'],  # 後処理用のスレッド数
    'prefer-insecure': True,            # 非セキュアな接続を許可
    'no-check-formats': True,           # フォーマットチェックをスキップ
    'allow_playlist_files': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'extractor_args': {
        'youtubetab': {
            'skip': ['authcheck']  # 認証チェックをスキップ
        }
    },
}

# FFmpeg用の音声処理オプション
FFMPEG_OPTIONS = {
    'options': '-vn -threads 4 -preset ultrafast -tune zerolatency',
    # -vn: 映像を無効化
    # -threads 4: 4スレッドで処理
    # -preset ultrafast: 最速の処理速度を優先
    # -tune zerolatency: 低遅延モードを有効化
}
