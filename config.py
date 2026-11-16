"""
Dev X Music 🎶 — Configuration
Telegram Group Voice Chat Music Bot (Pyrogram + PyTgCalls)
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Telegram API (from my.telegram.org/apps) ──
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")

    # ── Bot Token (from @BotFather) ──
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # ── MongoDB (from cloud.mongodb.com) ──
    MONGO_URL = os.getenv("MONGO_URL", "")

    # ── Logger & Owner ──
    LOGGER_ID = int(os.getenv("LOGGER_ID", 0))
    OWNER_ID = int(os.getenv("OWNER_ID", 0))

    # ── Pyrogram Session (from @StringFatherBot) ──
    SESSION = os.getenv("SESSION", None)

    # ── Limits ──
    DURATION_LIMIT = int(os.getenv("DURATION_LIMIT", 60)) * 60
    QUEUE_LIMIT = int(os.getenv("QUEUE_LIMIT", 20))
    PLAYLIST_LIMIT = int(os.getenv("PLAYLIST_LIMIT", 20))

    # ── Additional Sessions ──
    SESSION1 = os.getenv("SESSION1", None)
    SESSION2 = os.getenv("SESSION2", None)
    SESSION3 = os.getenv("SESSION3", None)

    # ── Support ──
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/DevXMusic")
    SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/DevXMusicChat")

    # ── Toggles ──
    AUTO_LEAVE = os.getenv("AUTO_LEAVE", "False").lower() == "true"
    AUTO_END = os.getenv("AUTO_END", "False").lower() == "true"
    THUMB_GEN = os.getenv("THUMB_GEN", "True").lower() == "true"
    VIDEO_PLAY = os.getenv("VIDEO_PLAY", "True").lower() == "true"
    LANG_CODE = os.getenv("LANG_CODE", "en")

    # ── Cookies ──
    COOKIES_URL = [
        url for url in os.getenv("COOKIES_URL", "").split(" ")
        if url and "batbin.me" in url
    ]

    # ── Images ──
    DEFAULT_THUMB = os.getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
    PING_IMG = os.getenv("PING_IMG", "https://files.catbox.moe/haagg2.png")
    START_IMG = os.getenv("START_IMG", "https://files.catbox.moe/zvziwk.jpg")

    # ── Bot Identity ──
    BOT_NAME = "Dev X Music 🎶"
    BOT_USERNAME = os.getenv("BOT_USERNAME", "")

    def check(self):
        missing = [
            var for var in [
                "API_ID", "API_HASH", "BOT_TOKEN",
                "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION"
            ]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(
                f"❌ Missing required environment variables: {', '.join(missing)}"
            )


config = Config()
