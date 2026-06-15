from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from urllib.parse import quote
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")


def search_deezer_multi(query, limit=5):
    """جستجو در Deezer و برگردوندن چند نتیجه"""
    try:
        resp = requests.get(
            "https://api.deezer.com/search",
            params={"q": query, "limit": limit},
            timeout=10,
        )
        items = resp.json().get("data", [])
        results = []
        for track in items:
            results.append({
                "id": track["id"],
                "title": track["title"],
                "artist": track["artist"]["name"],
            })
        return results
    except Exception as e:
        print(f"Deezer multi search error: {e}")
        return []


def search_genius_multi(query, limit=5):
    """جستجو در Genius و برگردوندن چند نتیجه"""
    try:
        response = requests.get(
            "https://api.genius.com/search",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"},
            params={"q": query},
            timeout=10,
        )
        hits = response.json()["response"]["hits"][:limit]
        results = []
        for hit in hits:
            song = hit["result"]
            results.append({
                "title": song["title"],
                "artist": song["primary_artist"]["name"],
            })
        return results
    except Exception as e:
        print(f"Genius multi search error: {e}")
        return []


def get_deezer_track(track_id):
    """گرفتن اطلاعات کامل یه ترک از Deezer"""
    try:
        t = requests.get(f"https://api.deezer.com/track/{track_id}", timeout=10).json()
        album_id = t["album"]["id"]
        album = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=10).json()
        artist_id = t["artist"]["id"]
        artist = requests.get(f"https://api.deezer.com/artist/{artist_id}", timeout=10).json()

        duration_sec = t.get("duration", 0)
        genres = [g["name"] for g in album.get("genres", {}).get("data", [])]
        fans = artist.get("nb_fan", 0)

        return {
            "title": t.get("title", "نامشخص"),
            "artist": t["artist"]["name"],
            "artist_fans": f"{fans:,}",
            "album": t["album"]["title"],
            "album_type": album.get("record_type", "نامشخص"),
            "release_date": album.get("release_date", "نامشخص"),
            "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
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
        print(f"Deezer track detail error: {e}")
        return None


def get_genius_info(title, artist):
    """گرفتن اطلاعات Genius برای یه آهنگ مشخص"""
    try:
        response = requests.get(
            "https://api.genius.com/search",
            headers={"Authorization": f"Bearer {GENIUS_TOKEN}"},
            params={"q": f"{artist} {title}"},
            timeout=10,
        )
        hits = response.json()["response"]["hits"]
        if not hits:
            return None
        song = hits[0]["result"]
        return {
            "url": song["url"],
            "image": song["song_art_image_url"],
            "release_date": song.get("release_date_for_display", "نامشخص"),
            "pageviews": song["stats"].get("pageviews", "نامشخص"),
            "annotations": song.get("annotation_count", "نامشخص"),
        }
    except Exception as e:
        print(f"Genius info error: {e}")
        return None


def build_message(title, artist, deezer, genius, youtube_link, google_link):
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

    # جستجوی چندتایی از Deezer و Genius
    deezer_results = search_deezer_multi(text, limit=5)
    genius_results = search_genius_multi(text, limit=5)

    # ترکیب نتایج و حذف تکراری‌ها
    seen = set()
    combined = []

    for item in deezer_results:
        key = f"{item['title'].lower()}_{item['artist'].lower()}"
        if key not in seen:
            seen.add(key)
            combined.append({"source": "deezer", "id": item["id"], "title": item["title"], "artist": item["artist"]})

    for item in genius_results:
        key = f"{item['title'].lower()}_{item['artist'].lower()}"
        if key not in seen:
            seen.add(key)
            combined.append({"source": "genius", "id": None, "title": item["title"], "artist": item["artist"]})

    combined = combined[:5]

    if not combined:
        await update.message.reply_text(
            "😔 آهنگی پیدا نشد.\n"
            "سعی کن اسم دقیق‌تری بنویسی یا چند کلمه از متن آهنگ بفرستی."
        )
        return

    # ذخیره نتایج در context برای استفاده بعدی
    context.user_data["search_results"] = combined

    # ساخت دکمه‌های انتخاب
    keyboard = []
    for i, item in enumerate(combined):
        label = f"🎵 {item['title']} — {item['artist']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔍 این آهنگا رو پیدا کردم، کدوم رو می‌خوای؟",
        reply_markup=reply_markup
    )


async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data)
    results = context.user_data.get("search_results", [])

    if not results or index >= len(results):
        await query.message.reply_text("❌ خطا، دوباره جستجو کن.")
        return

    selected = results[index]
    title = selected["title"]
    artist = selected["artist"]

    await query.message.reply_text("⏳ دارم اطلاعات کامل رو می‌گیرم...")

    # گرفتن اطلاعات کامل Deezer
    if selected["source"] == "deezer" and selected["id"]:
        deezer_result = get_deezer_track(selected["id"])
    else:
        # جستجوی مستقیم در Deezer با اسم آهنگ
        hits = search_deezer_multi(f"{artist} {title}", limit=1)
        if hits:
            deezer_result = get_deezer_track(hits[0]["id"])
        else:
            deezer_result = None

    # گرفتن اطلاعات Genius
    genius_result = get_genius_info(title, artist)

    youtube_link = f"https://www.youtube.com/results?search_query={quote(artist + ' ' + title)}"
    google_link = f"https://www.google.com/search?q={quote(artist + ' ' + title)}"

    cover_image = (
        (deezer_result and deezer_result.get("image"))
        or (genius_result and genius_result.get("image"))
    )

    message = build_message(title, artist, deezer_result, genius_result, youtube_link, google_link)

    if cover_image:
        await query.message.reply_photo(photo=cover_image, caption=message)
    else:
        await query.message.reply_text(message)

    # ارسال پیش‌نمایش ۳۰ ثانیه‌ای
    if deezer_result and deezer_result.get("preview_url"):
        await query.message.reply_audio(
            audio=deezer_result["preview_url"],
            title=title,
            performer=artist,
            caption="🎧 پیش‌نمایش ۳۰ ثانیه‌ای (Deezer)"
        )


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_selection))

print("Bot is running...")
app.run_polling()