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


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "درود دوست قشنگم💙\n"
        "لطفا یه تیکه از اهنگی که توی ذهنت هست رو برام بفرست"
    )


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

        data = response.json()

        hits = data["response"]["hits"]

        if not hits:
            return None

        song = hits[0]["result"]

        return {
            "title": song["title"],
            "artist": song["primary_artist"]["name"],
            "url": song["url"],
            "image": song["song_art_image_url"],

            "release_date":
                song.get(
                    "release_date_for_display",
                    "نامشخص"
                ),

            "pageviews":
                song["stats"].get(
                    "pageviews",
                    "نامشخص"
                ),

            "annotations":
                song.get(
                    "annotation_count",
                    "نامشخص"
                ),

            "artist_url":
                song["primary_artist"]["url"]
        }

    except Exception as e:
        print("ERROR:", e)
        return None


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    result = search_song(text)

    if result is None:

        await update.message.reply_text(
            "آهنگی پیدا نشد 😔"
        )

        return

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

    pageviews = result["pageviews"]

    if isinstance(pageviews, int):
        pageviews = f"{pageviews:,}"

    message = (

        f"🎵 {title}\n"
        f"🎤 {artist}\n\n"

        f"📅 Release Date:\n"
        f"{result['release_date']}\n\n"

        f"👀 Genius Views:\n"
        f"{pageviews}\n\n"

        f"📝 Annotations:\n"
        f"{result['annotations']}\n\n"

        f"🎼 Genius:\n"
        f"{result['url']}\n\n"

        f"🎧 Spotify:\n"
        f"{spotify_link}\n\n"

        f"▶️ YouTube:\n"
        f"{youtube_link}\n\n"

        f"🔍 Google:\n"
        f"{google_link}"
    )

    await update.message.reply_photo(
        photo=result["image"],
        caption=message
    )

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