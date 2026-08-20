import os
from aiohttp import web

from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from bot import bot, dp, init_db


PORT = int(os.getenv("PORT", "10000"))

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"


async def on_startup():
    await init_db()

    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL не установлен!")
        return

    await bot.set_webhook(
        url=f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    )

    print("✅ Webhook установлен:")
    print(f"{WEBHOOK_URL}{WEBHOOK_PATH}")


async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()


async def health(request):
    return web.Response(
        text="Anime bot is running!"
    )


app = web.Application()


app.router.add_get(
    "/",
    health
)


webhook_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
)

webhook_handler.register(
    app,
    path=WEBHOOK_PATH
)


dp.startup.register(
    on_startup
)

dp.shutdown.register(
    on_shutdown
)

setup_application(
    app,
    dp,
    bot=bot
)


if __name__ == "__main__":
    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
