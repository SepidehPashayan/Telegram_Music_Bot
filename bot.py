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
import base64
import time

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

_spotify_cache = {"token": None, "expires_at": 0}


def get_spotify_token():
    if _spotify_cache["token"] and time.time() < _spotify_cache["expires_at"]:
        return _spotify_cache["token"]

    credentials = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        data = resp.json()
        _spotify_cache["token"] = data["access_token"]
        _spotify_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
        return _spotify_cache["token"]
    except Exception as e:
        print(f"Spotify token error: {e}")
        return None


def search_spotify(query):
    token = get_spotify_token()
    if not token:
        return None

    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1},
            timeout=10,
        )
        tracks = resp.json().get("tracks", {}).get("items", [])
        if not tracks:
            return None

        track = tracks[0]
        album = track["album"]
        duration_sec = track["duration_ms"] // 1000

        return {
            "title": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": album["name"],
            "release_date": album.get("release_date", "نامشخص"),
            "spotify_url": track["external_urls"]["spotify"],
            "preview_url": track.get("preview_url"),
            "image": album["images"][0]["url"] if album["images"] else None,
            "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "popularity": track["popularity"],
        }
    except Exception as e:
        print(f"Spotify search error: {e}")
        return None


def search_genius(query):
    url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    params = {"q": query}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
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
            "release_date": song.get("release_date_for_display", "نامشخص"),
            "pageviews": song["stats"].get("pageviews", "نامشخص"),
            "annotations": song.get("annotation_count", "نامشخص"),
            "artist_url": song["primary_artist"]["url"]
        }
    except Exception as e:
        print("ERROR:", e)
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "درود دوست قشنگم💙\n"
        "لطفا یه تیکه از اهنگی که توی ذهنت هست رو برام بفرست"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # جستجو در Genius
    genius_result = search_genius(text)

    if genius_result is None:
        await update.message.reply_text("آهنگی پیدا نشد 😔")
        return

    title = genius_result["title"]
    artist = genius_result["artist"]

    # جستجو در Spotify با اسم دقیق آهنگ
    spotify_result = search_spotify(f"{artist} {title}")

    youtube_link = (
        f"https://www.youtube.com/results?"
        f"search_query={quote(artist + ' ' + title)}"
    )
    google_link = (
        f"https://www.google.com/search?"
        f"q={quote(artist + ' ' + title)}"
    )

    pageviews = genius_result["pageviews"]
    if isinstance(pageviews, int):
        pageviews = f"{pageviews:,}"

    # اگه Spotify پیدا کرد، لینک مستقیم - وگرنه لینک جستجو
    if spotify_result:
        spotify_link = spotify_result["spotify_url"]
        spotify_extra = (
            f"💿 آلبوم: {spotify_result['album']}\n"
            f"⏱ مدت: {spotify_result['duration']}\n"
            f"🔥 محبوبیت: {spotify_result['popularity']}/100\n\n"
        )
        cover_image = spotify_result["image"] or genius_result["image"]
    else:
        spotify_link = f"https://open.spotify.com/search/{quote(artist + ' ' + title)}"
        spotify_extra = ""
        cover_image = genius_result["image"]

    message = (
        f"🎵 {title}\n"
        f"🎤 {artist}\n\n"
        f"📅 Release Date:\n"
        f"{genius_result['release_date']}\n\n"
        f"{spotify_extra}"
        f"👀 Genius Views:\n"
        f"{pageviews}\n\n"
        f"📝 Annotations:\n"
        f"{genius_result['annotations']}\n\n"
        f"🎼 Genius:\n"
        f"{genius_result['url']}\n\n"
        f"🎧 Spotify:\n"
        f"{spotify_link}\n\n"
        f"▶️ YouTube:\n"
        f"{youtube_link}\n\n"
        f"🔍 Google:\n"
        f"{google_link}"
    )

    await update.message.reply_photo(
        photo=cover_image,
        caption=message
    )

    # ارسال پیش‌نمایش صوتی ۳۰ ثانیه‌ای از Spotify
    if spotify_result and spotify_result.get("preview_url"):
        await update.message.reply_audio(
            audio=spotify_result["preview_url"],
            title=title,
            performer=artist,
            caption="🎧 پیش‌نمایش ۳۰ ثانیه از Spotify"
        )
    else:
        await update.message.reply_text(
            "⚠️ فایل صوتی برای این آهنگ در Spotify موجود نیست."
        )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot is running...")
app.run_polling()