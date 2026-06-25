# 🎵 Telegram Music Bot

A Telegram bot that identifies songs based on their lyrics — send a lyric snippet and get back full song metadata including artist info, release date, cover art, and direct links to Genius, Spotify, YouTube, and Google.

> **Live & Deployed** on [Railway](https://railway.app)

---

## ✨ Features

- 🔍 **Lyric-based song search** — send any lyric fragment and the bot finds the matching song
- 🎨 **Rich song cards** — returns the album cover art alongside all metadata
- 📅 Release date & Genius page view count
- 📝 Annotation count from Genius community
- 🔗 Direct links to **Spotify**, **YouTube**, and **Google Search**
- ☁️ **Cloud-deployed** and always online via Railway

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.x |
| Bot Framework | `python-telegram-bot` v22.6 |
| Music Search API | [Genius API](https://genius.com/api-clients) |
| HTTP Client | `requests` v2.32.3 |
| Config Management | `python-dotenv` v1.2.2 |
| Deployment | [Railway](https://railway.app) |

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/SepidehPashayan/Telegram_Music_Bot.git
cd Telegram_Music_Bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
BOT_TOKEN=your_telegram_bot_token
GENIUS_TOKEN=your_genius_api_token
```

| Variable | How to Get |
|----------|-----------|
| `BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) on Telegram |
| `GENIUS_TOKEN` | Register at [genius.com/api-clients](https://genius.com/api-clients) and create a new API client |

### 4. Run the Bot

```bash
python bot.py
```

---

## 📖 How It Works

```
User sends a lyric  ──►  Genius API search  ──►  Extract metadata
                                                       │
                         ┌─────────────────────────────┘
                         ▼
              Return album art + song info + links
              (Genius · Spotify · YouTube · Google)
```

1. User sends `/start` to initialize the bot
2. User types any lyric snippet (e.g. `"never gonna give you up"`)
3. The bot queries the **Genius API** with the text
4. If a match is found, the bot replies with the album cover and a formatted message containing all metadata and links
5. If no match is found, the bot replies with a friendly error message

---

## 📂 Project Structure

```
Telegram_Music_Bot/
│
├── bot.py              # Main bot logic (handlers, Genius API, message formatting)
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
└── .gitignore
```

---

## 🔒 Environment Variables & Security

Sensitive credentials are managed through `.env` and never committed to version control. The `.gitignore` is configured to exclude the `.env` file.

---

## ☁️ Deployment

This bot is deployed on **Railway** for 24/7 availability.

To deploy your own instance:
1. Push the repository to GitHub
2. Connect the repo to [Railway](https://railway.app)
3. Add `BOT_TOKEN` and `GENIUS_TOKEN` as environment variables in the Railway dashboard
4. Deploy — Railway auto-detects Python and runs `bot.py`

---

## 📸 Demo

| User sends a lyric | Bot responds with song info |
|---|---|
| `"someone like you"` | 🎵 Someone Like You — Adele · Album art · Genius · Spotify · YouTube links |

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 👩‍💻 Author

**Sepideh Pashayan**  

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
