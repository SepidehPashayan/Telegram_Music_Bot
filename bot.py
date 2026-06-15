from telegram import Update
from urllib.parse import quote
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv
import os
import requests
import base64

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

_spotify_token_cache = {"token": None, "expires_at": 0}




def get_spotify_token() -> str | None:
    """Get a fresh Spotify access token using Client Credentials flow."""
    import time

    if _spotify_token_cache["token"] and time.time() < _spotify_token_cache["expires_at"]:
        return _spotify_token_cache["token"]

    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None

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
        token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        import time as _time
        _spotify_token_cache["token"] = token
        _spotify_token_cache["expires_at"] = _time.time() + expires_in - 60

        return token
    except Exception as e:
        print(f"Spotify token error: {e}")
        return None


def search_spotify(query: str) -> dict | None:
    """Search Spotify for a track. Returns structured result or None."""
    token = get_spotify_token()
    if not token:
        return None

    try:
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 5},
            timeout=10,
        )
        data = resp.json()
        tracks = data.get("tracks", {}).get("items", [])

        if not tracks:
            return None

        track = tracks[0]
        album = track["album"]
        artists = ", ".join(a["name"] for a in track["artists"])
        image_url = album["images"][0]["url"] if album["images"] else None
        preview_url = track.get("preview_url")  # 30-second preview MP3

        return {
            "source": "spotify",
            "title": track["name"],
            "artist": artists,
            "album": album["name"],
            "release_date": album.get("release_date", "نامشخص"),
            "spotify_url": track["external_urls"]["spotify"],
            "preview_url": preview_url,
            "image": image_url,
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],  # 0–100
        }
    except Exception as e:
        print(f"Spotify search error: {e}")
        return None


def search_genius(query: str) -> dict | None:
    """Search Genius API. Returns structured result or None."""
    if not GENIUS_TOKEN:
        return None

    try:
        resp = requests.get(
            "https://api.genius.com/search",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"},
            params={"q": query},
            timeout=10,
        )
        data = resp.json()
        hits = data["response"]["hits"]

        if not hits:
            return None

        song = hits[0]["result"]
        return {
            "source": "genius",
            "title": song["title"],
            "artist": song["primary_artist"]["name"],
            "url": song["url"],
            "image": song.get("song_art_image_url"),
            "release_date": song.get("release_date_for_display", "نامشخص"),
            "pageviews": song["stats"].get("pageviews", "نامشخص"),
            "annotations": song.get("annotation_count", "نامشخص"),
        }
    except Exception as e:
        print(f"Genius search error: {e}")
        return None



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "درود دوست قشنگم 💙\n"
        "یه تیکه از آهنگی که تو ذهنته رو برام بفرست\n"
        "یا اسم آهنگ و خواننده رو بنویس 🎵"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    await update.message.reply_text("🔍 دارم دنبالش می‌گردم...")

    # ── 1. Try Spotify first ──
    result = search_spotify(query)

    if result:
        await send_spotify_result(update, result, query)
        return

    # ── 2. Fallback to Genius ──
    result = search_genius(query)

    if result:
        await send_genius_result(update, result, query)
        return

    # ── 3. Nothing found ──
    await update.message.reply_text(
        "😔 متأسفم، آهنگی پیدا نشد.\n"
        "سعی کن اسم دقیق‌تری بنویسی یا چند کلمه از متن آهنگ بفرستی."
    )


async def send_spotify_result(update: Update, result: dict, query: str):
    duration_sec = result["duration_ms"] // 1000
    duration_fmt = f"{duration_sec // 60}:{duration_sec % 60:02d}"

    popularity_bar = "🟩" * (result["popularity"] // 20) + "⬜" * (5 - result["popularity"] // 20)

    youtube_link = f"https://www.youtube.com/results?search_query={quote(result['artist'] + ' ' + result['title'])}"
    google_link = f"https://www.google.com/search?q={quote(result['artist'] + ' ' + result['title'])}"

    caption = (
        f"✅ پیدا شد از Spotify!\n\n"
        f"🎵 {result['title']}\n"
        f"🎤 {result['artist']}\n"
        f"💿 {result['album']}\n\n"
        f"📅 تاریخ انتشار: {result['release_date']}\n"
        f"⏱ مدت: {duration_fmt}\n"
        f"🔥 محبوبیت: {popularity_bar} ({result['popularity']}/100)\n\n"
        f"🟢 Spotify:\n{result['spotify_url']}\n\n"
        f"▶️ YouTube:\n{youtube_link}\n\n"
        f"🔍 Google:\n{google_link}"
    )

    if result.get("image"):
        await update.message.reply_photo(photo=result["image"], caption=caption)
    else:
        await update.message.reply_text(caption)

    # Send 30s preview if available
    if result.get("preview_url"):
        await update.message.reply_audio(
            audio=result["preview_url"],
            title=result["title"],
            performer=result["artist"],
            caption="🎧 پیش‌نمایش ۳۰ ثانیه‌ای از Spotify",
        )


async def send_genius_result(update: Update, result: dict, query: str):
    youtube_link = f"https://www.youtube.com/results?search_query={quote(result['artist'] + ' ' + result['title'])}"
    spotify_link = f"https://open.spotify.com/search/{quote(result['artist'] + ' ' + result['title'])}"

    pageviews = result["pageviews"]
    if isinstance(pageviews, int):
        pageviews = f"{pageviews:,}"

    caption = (
        f"🎵 {result['title']}\n"
        f"🎤 {result['artist']}\n\n"
        f"📅 تاریخ انتشار: {result['release_date']}\n"
        f"👀 بازدید Genius: {pageviews}\n"
        f"📝 تعداد توضیحات: {result['annotations']}\n\n"
        f"🎼 Genius:\n{result['url']}\n\n"
        f"🎧 Spotify (جستجو):\n{spotify_link}\n\n"
        f"▶️ YouTube:\n{youtube_link}"
    )

    if result.get("image"):
        await update.message.reply_photo(photo=result["image"], caption=caption)
    else:
        await update.message.reply_text(caption)



app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()