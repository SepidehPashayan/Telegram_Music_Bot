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


def search_deezer(query):
    try:
        resp = requests.get(
            "https://api.deezer.com/search",
            params={"q": query, "limit": 1},
            timeout=10,
        )
        items = resp.json().get("data", [])
        if not items:
            return None

        track = items[0]
        track_id = track["id"]

        # اطلاعات کامل‌تر از endpoint آهنگ
        detail_resp = requests.get(
            f"https://api.deezer.com/track/{track_id}",
            timeout=10,
        )
        t = detail_resp.json()

        album_id = t["album"]["id"]
        album_resp = requests.get(
            f"https://api.deezer.com/album/{album_id}",
            timeout=10,
        )
        album = album_resp.json()

        artist_id = t["artist"]["id"]
        artist_resp = requests.get(
            f"https://api.deezer.com/artist/{artist_id}",
            timeout=10,
        )
        artist = artist_resp.json()

        duration_sec = t.get("duration", 0)
        duration_fmt = f"{duration_sec // 60}:{duration_sec % 60:02d}"

        genres = []
        if album.get("genres", {}).get("data"):
            genres = [g["name"] for g in album["genres"]["data"]]

        fans = artist.get("nb_fan", 0)
        fans_fmt = f"{fans:,}"

        return {
            "title": t.get("title", "نامشخص"),
            "artist": t["artist"]["name"],
            "artist_fans": fans_fmt,
            "album": t["album"]["title"],
            "album_type": album.get("record_type", "نامشخص"),
            "release_date": album.get("release_date", "نامشخص"),
            "duration": duration_fmt,
            "track_number": t.get("track_position", "نامشخص"),
            "total_tracks": album.get("nb_tracks", "نامشخص"),
            "disk_number": t.get("disk_number", 1),
            "explicit": t.get("explicit_lyrics", False),
            "bpm": t.get("bpm", 0),
            "gain": t.get("gain", 0),
            "rank": t.get("rank", 0),
            "genres": genres,
            "label": album.get("label", "نامشخص"),
            "image": album.get("cover_xl") or album.get("cover_big") or t["album"].get("cover_xl"),
            "preview_url": t.get("preview"),
            "deezer_url": t.get("link"),
            "artist_url": artist.get("link"),
        }
    except Exception as e:
        print(f"Deezer error: {e}")
        return None


def search_genius(query):
    try:
        response = requests.get(
            "https://api.genius.com/search",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"},
            params={"q": query},
            timeout=10,
        )
        hits = response.json()["response"]["hits"]
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
        print(f"Genius error: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "درود دوست قشنگم💙\n"
        "لطفا یه تیکه از اهنگی که توی ذهنت هست رو برام بفرست"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # اول از Genius اسم و خواننده رو پیدا می‌کنیم
    genius_result = search_genius(text)
    if genius_result is None:
        await update.message.reply_text("آهنگی پیدا نشد 😔")
        return

    title = genius_result["title"]
    artist = genius_result["artist"]

    # بعد با اسم دقیق از Deezer اطلاعات کامل می‌گیریم
    deezer_result = search_deezer(f"{artist} {title}")

    youtube_link = f"https://www.youtube.com/results?search_query={quote(artist + ' ' + title)}"
    google_link = f"https://www.google.com/search?q={quote(artist + ' ' + title)}"

    pageviews = genius_result["pageviews"]
    if isinstance(pageviews, int):
        pageviews = f"{pageviews:,}"

    if deezer_result:
        cover_image = deezer_result["image"] or genius_result["image"]
        explicit_tag = "🔞 Explicit" if deezer_result["explicit"] else "✅ Clean"
        genres_text = ", ".join(deezer_result["genres"][:3]) if deezer_result["genres"] else "نامشخص"

        rank = deezer_result["rank"]
        rank_bar = "🟩" * min(5, rank // 200000) + "⬜" * (5 - min(5, rank // 200000))

        bpm_text = f"{deezer_result['bpm']:.0f}" if deezer_result["bpm"] else "نامشخص"

        message = (
            f"🎵 {title}\n"
            f"🎤 {artist}\n\n"
            f"━━━━ 🟠 Deezer Info ━━━━\n"
            f"💿 آلبوم: {deezer_result['album']}\n"
            f"📀 نوع: {deezer_result['album_type']}\n"
            f"🎼 ترک: {deezer_result['track_number']} از {deezer_result['total_tracks']}\n"
            f"💽 دیسک: {deezer_result['disk_number']}\n"
            f"📅 انتشار: {deezer_result['release_date']}\n"
            f"⏱ مدت: {deezer_result['duration']}\n"
            f"{explicit_tag}\n"
            f"🎵 BPM: {bpm_text}\n"
            f"🏷 لیبل: {deezer_result['label']}\n"
            f"🎭 ژانر: {genres_text}\n"
            f"🔥 رنکینگ: {rank_bar} ({rank:,})\n"
            f"👥 فن‌های خواننده: {deezer_result['artist_fans']}\n\n"
            f"━━━━ 📖 Genius Info ━━━━\n"
            f"📅 انتشار: {genius_result['release_date']}\n"
            f"👀 بازدید: {pageviews}\n"
            f"📝 توضیحات: {genius_result['annotations']}\n\n"
            f"━━━━ 🔗 Links ━━━━\n"
            f"🟠 Deezer:\n{deezer_result['deezer_url']}\n\n"
            f"🎼 Genius:\n{genius_result['url']}\n\n"
            f"▶️ YouTube:\n{youtube_link}\n\n"
            f"🔍 Google:\n{google_link}"
        )
    else:
        cover_image = genius_result["image"]
        message = (
            f"🎵 {title}\n"
            f"🎤 {artist}\n\n"
            f"📅 انتشار: {genius_result['release_date']}\n"
            f"👀 بازدید Genius: {pageviews}\n"
            f"📝 توضیحات: {genius_result['annotations']}\n\n"
            f"🎼 Genius:\n{genius_result['url']}\n\n"
            f"▶️ YouTube:\n{youtube_link}\n\n"
            f"🔍 Google:\n{google_link}"
        )

    await update.message.reply_photo(photo=cover_image, caption=message)

    # ارسال پیش‌نمایش صوتی
    if deezer_result and deezer_result.get("preview_url"):
        await update.message.reply_audio(
            audio=deezer_result["preview_url"],
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