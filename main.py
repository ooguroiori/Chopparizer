# 必要なライブラリをインポート
import discord
from discord.ext import commands
from config.settings import DISCORD_TOKEN
from cogs.music import Music


# 音楽ボットのメインクラス
class MusicBot(commands.Bot):
    def __init__(self):
        # Discordボットの基本設定
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    # ボット起動時に実行される初期設定
    async def setup_hook(self):
        # 音楽機能(Cog)をボットに追加
        await self.add_cog(Music(self))


# メイン処理
def main():
    # ボットのインスタンスを作成
    bot = MusicBot()
    
    # ボット起動時のイベントハンドラ
    @bot.event
    async def on_ready():
        print(f'ボットが起動しました: {bot.user.name}')
        print('-------------------')

    # ボットを起動
    bot.run(DISCORD_TOKEN)


# スクリプトとして実行された場合にメイン処理を実行
if __name__ == "__main__":
    main()
