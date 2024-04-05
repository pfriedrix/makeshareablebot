from aiohttp import web

import logging
import sys
import asyncio

from bot import exchange_code, dp, bot
from db import init_db

async def spotify_callback(request):
    code = request.query.get('code')
    state = request.query.get('state')
    if not code or not state:
        return web.Response(text="No code provided", status=400)
    await exchange_code(code, state=state)
    return web.Response(text="Successfully! Can get back to the bot now")
  
app = web.Application()
app.router.add_get('/callback', spotify_callback)

async def run(): 
    init_db()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8881)
    await site.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
