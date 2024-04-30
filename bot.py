from aiogram import Bot, Dispatcher
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from aiogram.filters import CommandStart, Command
from aiogram.types import *
import uuid

from db import insert_or_update_spotify_token, get_spotify_token_from_db, remove_spotify_token
import os

SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
SPOTIFY_REDIRECT_URI = os.environ['SPOTIFY_REDIRECT_URI']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def exchange_code(code, state):
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-read-recently-played user-read-currently-playing",
                        state=state,
                        open_browser=False)
    
    tokenInfo = sp_oauth.get_access_token(code)
    await bot.send_message(int(state), "Successfully authenticated with Spotify!")
    insert_or_update_spotify_token(int(state), tokenInfo)

async def get_spotify_client(state):
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-read-recently-played user-read-currently-playing",
                        state=state,
                        open_browser=False)
   
    token_info = get_spotify_token_from_db(int(state))

    if not token_info:
        print("No cached token available")
        return None
    
    sp_oauth.get_access_token(token_info['access_token'])
    return Spotify(auth_manager=sp_oauth, requests_timeout=10, retries=3)

@dp.message(CommandStart())
async def send_welcome(message: Message):
    await message.reply("Hi!\nUse /login to authenticate with Spotify.\nUse /recent to get your recent tracks.")

@dp.message(Command("login"))
async def login(message: Message):
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-read-recently-played user-read-currently-playing",
                        state=str(message.from_user.id),
                        open_browser=False)
    url = sp_oauth.get_authorize_url()
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Authorize Spotify", url=url)]])
    await message.reply(f"Please authenticate with Spotify", reply_markup=inline_keyboard)

@dp.message(Command("logout"))
async def logout(message: Message):
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope="user-read-recently-played user-read-currently-playing",
                        state=str(message.from_user.id),
                        open_browser=False)
    remove_spotify_token(message.from_user.id)
    sp_oauth.cache_handler.save_token_to_cache({})
    await message.reply("Logged out")

@dp.message(Command("recent"))
async def recent_tracks(message: Message):
    sp = await get_spotify_client(message.from_user.id)
    if sp:
        results = sp.current_user_recently_played(limit=5)
        message_text = "Recent Tracks:\n\n"
        for idx, item in enumerate(results['items']):
            track = item['track']
            message_text += f"{idx + 1}. {track['name']} by {', '.join(artist['name'] for artist in track['artists'])}\n"
        await message.reply(message_text)
    else:
        await message.reply("You must authenticate with Spotify first.")

@dp.inline_query()
async def inline_recent_tracks(query: InlineQuery):
    user_query = query.query.lower() 
    
    sp = await get_spotify_client(query.from_user.id)

    if sp:
        response = sp.current_user_recently_played(limit=50)
        top_tracks = response['items']
        
        filtered_tracks = [track for track in top_tracks if user_query in track['track']['name'].lower()]
        
        results = []
        for track_info in filtered_tracks:
            track = track_info['track']
            artist = ', '.join(artist['name'] for artist in track['artists'])
            result = InlineQueryResultAudio(
                id=str(uuid.uuid4()),
                audio_url=track['preview_url'],
                title=f"{track['name']}",
                performer=artist,
                caption=f"{artist} - {track['name']}",
                audio_duration=int(track['duration_ms'] / 1000),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Spotify", url=track['external_urls']['spotify'])]])
            )
            results.append(result)
        
        current = sp.currently_playing()
        if current:
            result = InlineQueryResultAudio(
                id=str(uuid.uuid4()),
                audio_url=current['item']['preview_url'],
                title=f"{current['item']['name']}",
                performer=', '.join(artist['name'] for artist in current['item']['artists']),
                caption=f"{', '.join(artist['name'] for artist in current['item']['artists'])} - {current['item']['name']}",
                audio_duration=int(current['item']['duration_ms'] / 1000),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Spotify", url=current['item']['external_urls']['spotify'])]])
            )
            results.insert(0, result)

        await query.answer(results[:5], cache_time=1, is_personal=True)
    else:
        await query.answer([InlineQueryResultArticle(
            id="1",
            title="Authenticate with Spotify",
            input_message_content=InputTextMessageContent(message_text="/login")
        )], cache_time=1)