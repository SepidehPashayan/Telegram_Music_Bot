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
import yt_dlp

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
        # جستجوی آهنگ
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
        track_id = track["id"]
        album_id = album["id"]

        # اطلاعات کامل‌تر آلبوم
        album_resp = requests.get(
            f"https://api.spotify.com/v1/albums/{album_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        album_data = album_resp.json()
        genres = album_data.get("genres", [])
        label = album_data.get("label", "نامشخص")
        total_tracks = album_data.get("total_tracks", "نامشخص")

        # اطلاعات خواننده
        artist_id = track["artists"][0]["id"]
        artist_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        artist_data = artist_resp.json()
        artist_genres = artist_data.get("genres", [])
        artist_followers = artist_data.get("followers", {}).get("total", 0)
        artist_popularity = artist_data.get("popularity", 0)

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
            "total_tracks": total_tracks,
            "disc_number": track.get("disc_number", 1),
            "isrc": track.get("external_ids", {}).get("isrc", "نامشخص"),
            "label": label,
            "genres": genres if genres else artist_genres,
            "artist_followers": f"{artist_followers:,}",
            "artist_popularity": artist_popularity,
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


def download_audio_youtube(artist, title):
    """دانلود فایل صوتی از یوتیوب"""
    query = f"{artist} {title} official audio"
    output_path = f"/tmp/{artist}_{title}".replace(" ", "_")[:50]

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path + ".%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "max_filesize": 45 * 1024 * 1024,  # حداکثر ۴۵ مگ (تلگرام ۵۰ مگ قبول می‌کنه)
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        return output_path + ".mp3"
    except Exception as e:
        print(f"YouTube download error: {e}")
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

    # جستجو در Spotify
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
            f"━━━━━━ 🟢 Spotify Info ━━━━━━\n"
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
            f"━━━━━━ 📖 Genius Info ━━━━━━\n"
            f"📅 انتشار: {genius_result['release_date']}\n"
            f"👀 بازدید: {pageviews}\n"
            f"📝 توضیحات: {genius_result['annotations']}\n\n"
            f"━━━━━━ 🔗 Links ━━━━━━\n"
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
            f"📅 Release Date:\n"
            f"{genius_result['release_date']}\n\n"
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

    # دانلود و ارسال فایل صوتی از یوتیوب
    await update.message.reply_text("🎵 دارم فایل صوتی رو دانلود می‌کنم...")
    audio_path = download_audio_youtube(artist, title)

    if audio_path and os.path.exists(audio_path):
        with open(audio_path, "rb") as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                caption="🎧 فایل صوتی آهنگ"
            )
        os.remove(audio_path)
    else:
        await update.message.reply_text("⚠️ دانلود فایل صوتی موفق نبود.")


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