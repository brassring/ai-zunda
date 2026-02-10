import logging

import aiohttp
import discord
from discord.ext import commands
from ollama import AsyncClient as OllamaClient

from .config import TOKEN, setup_logging
from .db import init_db, close_db

log = logging.getLogger(__name__)


def main():
    setup_logging()

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)

    async def _setup_hook():
        bot.http_session = aiohttp.ClientSession()
        bot.ollama_client = OllamaClient()
        await init_db()
        await bot.load_extension("ai_zunda.cogs.voice")
        log.info("セットアップ完了")

    bot.setup_hook = _setup_hook

    original_close = bot.close

    async def _close():
        if hasattr(bot, "http_session"):
            await bot.http_session.close()
            log.info("HTTP セッションを閉じました")
        await close_db()
        await original_close()

    bot.close = _close

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
