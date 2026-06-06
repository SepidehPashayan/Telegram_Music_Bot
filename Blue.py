from telegram import Update
import requests
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

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "سلام 🌸\n"
        "یه تیکه از متن آهنگ رو برام بفرست."
    )

def search_song(query):
    url = "https://itunes.apple.com/search"

    params = {
        "term": query,
        "entity": "song",
        "limit": 1
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["resultCount"] == 0:
        return None

    song = data["results"][0]

    return {
        "title": song["trackName"],
        "artist": song["artistName"],
        "album": song["collectionName"],
        "cover": song["artworkUrl100"]
    }

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text

    result = search_song(text)

    if not result:
        await update.message.reply_text(
            "آهنگی پیدا نشد 😔"
        )
        return

    title = result["title"]
    artist = result["artist"]
    album = result["album"]

    youtube_link = (
        f"https://www.youtube.com/results?"
        f"search_query={quote(artist + ' ' + title)}"
    )

    google_link = (
        f"https://www.google.com/search?"
        f"q={quote(artist + ' ' + title)}"
    )

    message = (
        f"🎵 {title}\n"
        f"🎤 {artist}\n"
        f"💿 {album}\n\n"
        f"▶️ YouTube:\n{youtube_link}\n\n"
        f"🔍 Google:\n{google_link}"
    )

    await update.message.reply_photo(
        photo=result["cover"],
        caption=message
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot is running...")

app.run_polling()