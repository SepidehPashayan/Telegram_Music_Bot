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
        print(f"Spotify token status: {resp.status_code}")
        print(f"Spotify token response: {resp.text[:200]}")

        if resp.status_code != 200:
            return None

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
        print("No Spotify token available")
        return None

    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1},
            timeout=10,
        )
        print(f"Spotify search status: {resp.status_code}")

        if resp.status_code != 200:
            return None

        tracks = resp.json().get("tracks", {}).get("items", [])
        if not tracks:
            return None

        track = tracks[0]
        album = track["album"]
        duration_sec = track["duration_ms"] // 1000
        album_id = album["id"]
        artist_id = track["artists"][0]["id"]

        # اطلاعات آلبوم
        album_resp = requests.get(
            f"https://api.spotify.com/v1/albums/{album_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        album_data = album_resp.json() if album_resp.status_code == 200 else {}

        # اطلاعات خواننده
        artist_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        artist_data = artist_resp.json() if artist_resp.status_code == 200 else {}

        genres = album_data.get("genres", []) or artist_data.get("genres", [])
        artist_followers = artist_data.get("followers", {}).get("total", 0)

        return {
            "title": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": album["name"],
            "album_type": album.get("album_type", "نامشخص"),
            "release_date": album.get("release_date", "نامشخص"),
            "spotify_url": track["external_urls"]["spotify"],
            "image": album["images"][0]["url"] if album["images"] else None,
            "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "popularity": track["popularity"],
            "explicit": track.get("explicit", False),
            "track_number": track.get("track_number", "نامشخص"),
            "total_tracks": album_data.get("total_tracks", "نامشخص"),
            "label": album_data.get("label", "نامشخص"),
            "genres": genres,
            "isrc": track.get("external_ids", {}).get("isrc", "نامشخص"),
            "artist_followers": f"{artist_followers:,}",
            "artist_popularity": artist_data.get("popularity", 0),
        }
    except Exception as e:
        print(f"Spotify search error: {e}")
        return None


def search_deezer(artist, title):
    """جستجو در Deezer برای گرفتن preview 30 ثانیه‌ای"""
    try:
        resp = requests.get(
            "https://api.deezer.com/search",
            params={"q": f"{artist} {title}", "limit": 1},
            timeout=10,
        )
        data = resp.json()
        items = data.get("data", [])
        if not items:
            return None

        track = items[0]
        return track.get("preview")  # لینک mp3 30 ثانیه‌ای
    except Exception as e:
        print(f"Deezer error: {e}")
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

    genius_result = search_genius(text)
    if genius_result is None:
        await update.message.reply_text("آهنگی پیدا نشد 😔")
        return

    title = genius_result["title"]
    artist = genius_result["artist"]

    spotify_result = search_spotify(f"{artist} {title}")

    youtube_link = f"https://www.youtube.com/results?search_query={quote(artist + ' ' + title)}"
    google_link = f"https://www.google.com/search?q={quote(artist + ' ' + title)}"

    pageviews = genius_result["pageviews"]
    if isinstance(pageviews, int):
        pageviews = f"{pageviews:,}"

    if spotify_result:
        spotify_link = spotify_result["spotify_url"]
        cover_image = spotify_result["image"] or genius_result["image"]
        explicit_tag = "🔞 Explicit" if spotify_result["explicit"] else "✅ Clean"
        genres_text = ", ".join(spotify_result["genres"][:3]) if spotify_result["genres"] else "نامشخص"
        popularity_bar = "🟩" * (spotify_result["popularity"] // 20) + "⬜" * (5 - spotify_result["popularity"] // 20)
        artist_pop_bar = "🟦" * (spotify_result["artist_popularity"] // 20) + "⬜" * (5 - spotify_result["artist_popularity"] // 20)

        message = (
            f"🎵 {title}\n"
            f"🎤 {artist}\n\n"
            f"━━━━ 🟢 Spotify Info ━━━━\n"
            f"💿 آلبوم: {spotify_result['album']}\n"
            f"📀 نوع: {spotify_result['album_type']}\n"
            f"🎼 ترک: {spotify_result['track_number']} از {spotify_result['total_tracks']}\n"
            f"📅 انتشار: {spotify_result['release_date']}\n"
            f"⏱ مدت: {spotify_result['duration']}\n"
            f"{explicit_tag}\n"
            f"🏷 لیبل: {spotify_result['label']}\n"
            f"🎭 ژانر: {genres_text}\n"
            f"🔥 محبوبیت آهنگ: {popularity_bar} ({spotify_result['popularity']}/100)\n"
            f"👤 محبوبیت خواننده: {artist_pop_bar} ({spotify_result['artist_popularity']}/100)\n"
            f"👥 فالوور خواننده: {spotify_result['artist_followers']}\n"
            f"🆔 ISRC: {spotify_result['isrc']}\n\n"
            f"━━━━ 📖 Genius Info ━━━━\n"
            f"📅 انتشار: {genius_result['release_date']}\n"
            f"👀 بازدید: {pageviews}\n"
            f"📝 توضیحات: {genius_result['annotations']}\n\n"
            f"━━━━ 🔗 Links ━━━━\n"
            f"🎧 Spotify:\n{spotify_link}\n\n"
            f"🎼 Genius:\n{genius_result['url']}\n\n"
            f"▶️ YouTube:\n{youtube_link}\n\n"
            f"🔍 Google:\n{google_link}"
        )
    else:
        cover_image = genius_result["image"]
        spotify_link = f"https://open.spotify.com/search/{quote(artist + ' ' + title)}"
        message = (
            f"🎵 {title}\n"
            f"🎤 {artist}\n\n"
            f"📅 Release Date: {genius_result['release_date']}\n"
            f"👀 Genius Views: {pageviews}\n"
            f"📝 Annotations: {genius_result['annotations']}\n\n"
            f"🎼 Genius:\n{genius_result['url']}\n\n"
            f"🎧 Spotify:\n{spotify_link}\n\n"
            f"▶️ YouTube:\n{youtube_link}\n\n"
            f"🔍 Google:\n{google_link}"
        )

    await update.message.reply_photo(photo=cover_image, caption=message)

    # پیش‌نمایش صوتی از Deezer
    preview_url = search_deezer(artist, title)
    if preview_url:
        await update.message.reply_audio(
            audio=preview_url,
            title=title,
            performer=artist,
            caption="🎧 پیش‌نمایش ۳۰ ثانیه‌ای (Deezer)"
        )
    else:
        await update.message.reply_text("⚠️ پیش‌نمایش صوتی موجود نیست.")


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()