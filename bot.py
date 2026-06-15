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

        detail_resp = requests.get(f"https://api.deezer.com/track/{track_id}", timeout=10)
        t = detail_resp.json()

        album_id = t["album"]["id"]
        album_resp = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=10)
        album = album_resp.json()

        artist_id = t["artist"]["id"]
        artist_resp = requests.get(f"https://api.deezer.com/artist/{artist_id}", timeout=10)
        artist = artist_resp.json()

        duration_sec = t.get("duration", 0)
        duration_fmt = f"{duration_sec // 60}:{duration_sec % 60:02d}"

        genres = []
        if album.get("genres", {}).get("data"):
            genres = [g["name"] for g in album["genres"]["data"]]

        fans = artist.get("nb_fan", 0)

        return {
            "title": t.get("title", "نامشخص"),
            "artist": t["artist"]["name"],
            "artist_fans": f"{fans:,}",
            "artist_url": artist.get("link"),
            "album": t["album"]["title"],
            "album_type": album.get("record_type", "نامشخص"),
            "release_date": album.get("release_date", "نامشخص"),
            "duration": duration_fmt,
            "track_number": t.get("track_position", "نامشخص"),
            "total_tracks": album.get("nb_tracks", "نامشخص"),
            "disk_number": t.get("disk_number", 1),
            "explicit": t.get("explicit_lyrics", False),
            "bpm": t.get("bpm", 0),
            "rank": t.get("rank", 0),
            "genres": genres,
            "label": album.get("label", "نامشخص"),
            "image": album.get("cover_xl") or album.get("cover_big"),
            "preview_url": t.get("preview"),
            "deezer_url": t.get("link"),
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


def build_message(title, artist, deezer, genius, youtube_link, google_link):
    """ساخت پیام نهایی"""

    if deezer:
        explicit_tag = "🔞 Explicit" if deezer["explicit"] else "✅ Clean"
        genres_text = ", ".join(deezer["genres"][:3]) if deezer["genres"] else "نامشخص"
        rank = deezer["rank"]
        rank_bar = "🟩" * min(5, rank // 200000) + "⬜" * (5 - min(5, rank // 200000))
        bpm_text = f"{deezer['bpm']:.0f}" if deezer["bpm"] else "نامشخص"

        deezer_section = (
            f"━━━━ 🟠 Deezer Info ━━━━\n"
            f"💿 آلبوم: {deezer['album']}\n"
            f"📀 نوع: {deezer['album_type']}\n"
            f"🎼 ترک: {deezer['track_number']} از {deezer['total_tracks']}\n"
            f"💽 دیسک: {deezer['disk_number']}\n"
            f"📅 انتشار: {deezer['release_date']}\n"
            f"⏱ مدت: {deezer['duration']}\n"
            f"{explicit_tag}\n"
            f"🎵 BPM: {bpm_text}\n"
            f"🏷 لیبل: {deezer['label']}\n"
            f"🎭 ژانر: {genres_text}\n"
            f"🔥 رنکینگ: {rank_bar} ({rank:,})\n"
            f"👥 فن‌های خواننده: {deezer['artist_fans']}\n\n"
        )
        deezer_link = f"🟠 Deezer:\n{deezer['deezer_url']}\n\n"
    else:
        deezer_section = ""
        deezer_link = ""

    if genius:
        pageviews = genius["pageviews"]
        if isinstance(pageviews, int):
            pageviews = f"{pageviews:,}"
        genius_section = (
            f"━━━━ 📖 Genius Info ━━━━\n"
            f"📅 انتشار: {genius['release_date']}\n"
            f"👀 بازدید: {pageviews}\n"
            f"📝 توضیحات: {genius['annotations']}\n\n"
        )
        genius_link = f"🎼 Genius:\n{genius['url']}\n\n"
    else:
        genius_section = ""
        genius_link = ""

    return (
        f"🎵 {title}\n"
        f"🎤 {artist}\n\n"
        f"{deezer_section}"
        f"{genius_section}"
        f"━━━━ 🔗 Links ━━━━\n"
        f"{deezer_link}"
        f"{genius_link}"
        f"▶️ YouTube:\n{youtube_link}\n\n"
        f"🔍 Google:\n{google_link}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "درود دوست قشنگم💙\n"
        "لطفا یه تیکه از اهنگی که توی ذهنت هست رو برام بفرست"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # مرحله ۱: جستجو در Genius
    genius_result = search_genius(text)

    if genius_result:
        title = genius_result["title"]
        artist = genius_result["artist"]
        # با اسم دقیق از Deezer هم بگیر
        deezer_result = search_deezer(f"{artist} {title}")
    else:
        # مرحله ۲: اگه Genius پیدا نکرد، مستقیم از Deezer جستجو کن
        print(f"Genius failed, trying Deezer directly for: {text}")
        deezer_result = search_deezer(text)

        if deezer_result:
            title = deezer_result["title"]
            artist = deezer_result["artist"]
        else:
            # مرحله ۳: هیچ‌کدام پیدا نکردند
            await update.message.reply_text(
                "😔 آهنگی پیدا نشد.\n"
                "سعی کن اسم دقیق‌تری بنویسی یا چند کلمه از متن آهنگ بفرستی."
            )
            return

    youtube_link = f"https://www.youtube.com/results?search_query={quote(artist + ' ' + title)}"
    google_link = f"https://www.google.com/search?q={quote(artist + ' ' + title)}"

    cover_image = (
        (deezer_result and deezer_result.get("image"))
        or (genius_result and genius_result.get("image"))
    )

    message = build_message(title, artist, deezer_result, genius_result, youtube_link, google_link)

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