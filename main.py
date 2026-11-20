import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

import config
from handlers.common import router as common_router
from handlers.ai import router as ai_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AntigravityBot")

async def start_health_server():
    """Запускает мини HTTP-сервер для health check (требуется для Render, Koyeb и других облачных хостингов)."""
    app = web.Application()
    
    async def handle_ping(request):
        return web.Response(text="🌌 Antigravity AI Bot is running 24/7!", content_type="text/plain; charset=utf-8")
    
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health-check HTTP сервер запущен на порту {port}")

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="new", description="✨ Начать новый диалог"),
        BotCommand(command="model", description="🧠 Выбор модели AI"),
        BotCommand(command="help", description="💡 Возможности Antigravity"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Не удалось установить команды: {e}")

async def main():
    token = config.get_bot_token()
    if not token:
        print("[!] Ошибка: bot_token не указан в config.json или переменных окружения.")
        sys.exit(1)

    proxy = config.get_proxy()
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        logger.info(f"Используется локальный прокси: {proxy}")
        session = AiohttpSession(proxy=proxy)
        bot = Bot(token=token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    else:
        # На облачном сервере/хостинге прямой коннект без прокси
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    dp = Dispatcher()
    dp.include_router(common_router)
    dp.include_router(ai_router)

    me = await bot.get_me()
    logger.info(f"Antigravity AI успешно запущен: @{me.username} (ID: {me.id})")
    
    await set_bot_commands(bot)
    await start_health_server()

    print("\n" + "=" * 65)
    print(f"🌌 Antigravity AI готов к работе: https://t.me/{me.username}")
    print("=" * 65 + "\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n[!] Бот остановлен.")
