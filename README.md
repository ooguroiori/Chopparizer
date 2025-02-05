# Discordの音楽bot(2025/02/06更新)

## 使用方法

| 機能               | コマンド    |
| ------------------ | ----------- |
| 曲の再生           | !play [URL] |
| 曲の停止(退出)     | !stop       |
| 曲の一次停止       | !pause      |
| 曲の再開           | !resume     |
| キューの確認       | !queue      |
| 曲のスキップ       | !skip       |
| キューのリピート   | !repeat     |
| キューのシャッフル | !shuffle    |

## botの起動方法

`.env`にdiscordbotのトークンを記述

`python main.py`でbot起動

## ディレクトリ構造

```
Chopparizer/
├── __init__.py                 # Pythonパッケージとして認識させるための空ファイル
├── main.py                     # ボットのメインエントリーポイント、起動処理を担当
├── config/
│   ├── __init__.py            # configパッケージの初期化ファイル
│   └── settings.py            # 環境変数やYTDL、FFmpegの設定を管理
├── cogs/
│   ├── __init__.py            # cogsパッケージの初期化ファイル
│   └── music.py               # 音楽機能の全コマンドとロジックを実装
├── models/
│   ├── __init__.py            # modelsパッケージの初期化ファイル
│   └── music_source.py        # YouTube音源の取得と変換を担当
└── utils/
├── __init__.py            # utilsパッケージの初期化ファイル
└── youtube.py             # YouTubeダウンロード用のユーティリティ関数を提供
```



## 依存関係

そのうち記述予定


