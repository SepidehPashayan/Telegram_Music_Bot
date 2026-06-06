from telegram import Update
from urllib.parse import quote
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from dotenv import load_dotenv
import os
import requests

# =========================
# ENV
# =========================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")

# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "سلام 🌸\n"
        "یه تیکه از متن آهنگ رو برام بفرست."
    )

# =========================
# GENIUS SEARCH
# =========================

def search_song(query):

    url = "https://api.genius.com/search"

    headers = {
        "Authorization": f"Bearer {GENIUS_TOKEN}"
    }

    params = {
        "q": query
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        print("Status Code:", response.status_code)

        data = response.json()

        print(data)

        hits = data["response"]["hits"]

        if len(hits) == 0:
            return None

        song = hits[0]["result"]

        return {
            "title": song["title"],
            "artist": song["primary_artist"]["name"],
            "url": song["url"],
            "image": song["song_art_image_url"]
        }

    except Exception as e:
        print("ERROR:", e)
        return None

# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    print("User Message:", text)

    result = search_song(text)
    
    title = result["title"]
    artist = result["artist"]

    youtube_link = (
        f"https://www.youtube.com/results?"
        f"search_query={quote(artist + ' ' + title)}"
    )
    google_link = (
    f"https://www.google.com/search?"
    f"q={quote(artist + ' ' + title)}"
    )
    spotify_link = (
    f"https://open.spotify.com/search/"
    f"{quote(artist + ' ' + title)}"
    )

    print("Result:", result)

    if result is None:
        await update.message.reply_text(
            "آهنگی پیدا نشد 😔"
        )
        return

    message = (
    f"🎵 {title}\n"
    f"🎤 {artist}\n\n"

    f"🎼 Genius:\n"
    f"{result['url']}\n\n"

    f"▶️ YouTube:\n"
    f"{youtube_link}\n\n"

    f"🎧 Spotify:\n"
    f"{spotify_link}\n\n"

    f"🔍 Google:\n"
    f"{google_link}"
    )

    await update.message.reply_photo(
        photo=result["image"],
        caption=message
    )

# =========================
# APP
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot is running...")

app.run_polling()