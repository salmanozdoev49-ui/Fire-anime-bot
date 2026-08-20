import os
import asyncio

from aiohttp import web

from bot import dp, bot, init_db


PORT = int(os.getenv("PORT", 10000))


async def handle_webhook(request):
    return web.Response(text="Bot is running!")


async def on_startup(app):
    await init_db()

    webhook_url = os.getenv("WEBHOOK_URL")

    if webhook_url:
        await bot.set_webhook(
            url=f"{webhook_url}/webhook"
        )

        print("Webhook установлен:")
        print(f"{webhook_url}/webhook")
    else:
        print("WEBHOOK_URL не установлен!")


async def on_shutdown(app):
    await bot.delete_webhook()


app = web.Application()

app.router.add_post(
    "/webhook",
    lambda request: web.Response(text="OK")
)

app.router.add_get(
    "/",
    handle_webhook
)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)


if __name__ == "__main__":
    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
)
