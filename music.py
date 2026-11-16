#!/usr/bin/env python3
"""
Dev X Music 🎶 — Telegram Group Voice Chat Music Bot
Powered by Pyrogram + PyTgCalls + yt-dlp + MongoDB

Features:
  • /play  — Play audio in group voice chat
  • /vplay — Play video in group voice chat
  • /skip  — Skip current track
  • /stop  — Stop playback & leave voice chat
  • /pause — Pause playback
  • /resume — Resume playback
  • /queue — Show current queue
  • /playlist — Manage saved playlists
  • /auth — Authorize users
  • /settings — Bot settings
  • /ping — Ping test

Deploy on Heroku:
  1. heroku create devx-music
  2. heroku addons:create mongolab:sandbox
  3. heroku config:set API_ID=... API_HASH=... BOT_TOKEN=... MONGO_URL=... LOGGER_ID=... OWNER_ID=... SESSION=...
  4. git push heroku main
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import motor.motor_asyncio
from PIL import Image, ImageOps
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import (
    HighQualityAudio,
    HighQualityVideo,
)
from pytgcalls.types.stream import StreamTypeEnded
from yt_dlp import YoutubeDL

from config import config

# ═════════════════════════════════════════════════════════════════════
#  DATABASE
# ═════════════════════════════════════════════════════════════════════

db = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URL).devxmusic
db_chats = db.chats
db_queue = db.queue
db_playlists = db.playlists
db_auth = db.auth
db_settings = db.settings


async def is_served_chat(chat_id: int) -> bool:
    return await db_chats.find_one({"chat_id": chat_id}) is not None


async def add_served_chat(chat_id: int):
    await db_chats.update_one(
        {"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True
    )


async def get_queue(chat_id: int) -> List[dict]:
    doc = await db_queue.find_one({"chat_id": chat_id})
    return doc.get("queue", []) if doc else []


async def add_to_queue(chat_id: int, track: dict):
    await db_queue.update_one(
        {"chat_id": chat_id},
        {"$push": {"queue": track}},
        upsert=True,
    )


async def clear_queue(chat_id: int):
    await db_queue.delete_one({"chat_id": chat_id})


async def get_playlist(user_id: int) -> List[dict]:
    doc = await db_playlists.find_one({"user_id": user_id})
    return doc.get("playlist", []) if doc else []


async def save_playlist(user_id: int, playlist: List[dict]):
    await db_playlists.update_one(
        {"user_id": user_id},
        {"$set": {"playlist": playlist}},
        upsert=True,
    )


async def is_auth(user_id: int, chat_id: int) -> bool:
    if user_id == config.OWNER_ID:
        return True
    doc = await db_auth.find_one({"user_id": user_id, "chat_id": chat_id})
    return doc is not None


async def add_auth(user_id: int, chat_id: int):
    await db_auth.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"$set": {"user_id": user_id, "chat_id": chat_id}},
        upsert=True,
    )


# ═════════════════════════════════════════════════════════════════════
#  YT-DLP HELPERS
# ═════════════════════════════════════════════════════════════════════

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extractaudio": True,
    "audioformat": "mp3",
    "noplaylist": True,
}

YDL_VIDEO_OPTS = {
    "format": "bestvideo+bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}


async def extract_info(url: str, video: bool = False) -> Optional[dict]:
    """Extract track info from URL using yt-dlp."""
    opts = YDL_VIDEO_OPTS if video else YDL_OPTS
    loop = asyncio.get_event_loop()

    def _extract():
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await loop.run_in_executor(None, _extract)
        if not info:
            return None
        return {
            "title": info.get("title", "Unknown Title"),
            "duration": info.get("duration", 0),
            "url": info.get("url") or url,
            "webpage_url": info.get("webpage_url") or url,
            "uploader": info.get("uploader", "Unknown"),
            "thumbnail": info.get("thumbnail"),
        }
    except Exception as e:
        print(f"[yt-dlp] Error: {e}")
        return None


def format_duration(seconds: int) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


# ═════════════════════════════════════════════════════════════════════
#  IMAGE HELPERS (rotation fix)
# ═════════════════════════════════════════════════════════════════════

START_IMG_URL = "https://files.catbox.moe/lrv2hq.jpg"


async def fix_image_rotation(url: str, output_path: str = "start_img_fixed.jpg") -> str:
    """Download image, fix EXIF rotation, save locally."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return url
            data = await resp.read()

    with open(output_path, "wb") as f:
        f.write(data)

    try:
        img = Image.open(output_path)
        # Apply EXIF transpose to fix rotation
        img = ImageOps.exif_transpose(img)
        img.save(output_path, "JPEG")
        return output_path
    except Exception as e:
        print(f"[Image] Rotation fix failed: {e}")
        return output_path


# ═════════════════════════════════════════════════════════════════════
#  CLIENTS
# ═════════════════════════════════════════════════════════════════════

app = Client(
    "devxmusic",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

userbot = Client(
    "devxmusic_user",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION,
)

pytgcalls = PyTgCalls(userbot)

# Per-chat active call state
active_calls: Dict[int, dict] = {}

# ═════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═════════════════════════════════════════════════════════════════════

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add to Group", url="https://t.me/" + config.BOT_USERNAME + "?startgroup=true"),
                InlineKeyboardButton("🆘 Support", url=config.SUPPORT_CHAT),
            ],
            [
                InlineKeyboardButton("📢 Channel", url=config.SUPPORT_CHANNEL),
                InlineKeyboardButton("👤 Owner", url=f"tg://user?id={config.OWNER_ID}"),
            ],
        ]
    )


def control_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause|{chat_id}"),
                InlineKeyboardButton("▶ Resume", callback_data=f"resume|{chat_id}"),
            ],
            [
                InlineKeyboardButton("⏭ Skip", callback_data=f"skip|{chat_id}"),
                InlineKeyboardButton("⏹ Stop", callback_data=f"stop|{chat_id}"),
            ],
        ]
    )


# ═════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message: Message):
    text = (
        f"🎵 **Welcome to {config.BOT_NAME}!**\n\n"
        "I'm a powerful Telegram group voice chat music bot.\n\n"
        "**Features:**\n"
        "• /play — Play audio in voice chat\n"
        "• /vplay — Play video in voice chat\n"
        "• /skip — Skip current track\n"
        "• /stop — Stop & leave voice chat\n"
        "• /pause — Pause playback\n"
        "• /resume — Resume playback\n"
        "• /queue — Show current queue\n"
        "• /playlist — Manage playlists\n\n"
        "Add me to your group and start playing music! 🎶"
    )
    # Fix rotation and send image
    fixed_img = await fix_image_rotation(START_IMG_URL)
    await message.reply_photo(
        photo=fixed_img,
        caption=text,
        reply_markup=start_keyboard(),
    )


@app.on_message(filters.command("ping"))
async def ping_cmd(_, message: Message):
    start = time.time()
    m = await message.reply("🏓 Pinging...")
    end = time.time()
    await m.edit(
        f"🏓 **Pong!**\n"
        f"⚡ `{round((end - start) * 1000)} ms`\n"
        f"🤖 **{config.BOT_NAME}**"
    )


@app.on_message(filters.command("play") & filters.group)
async def play_cmd(_, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply(
            "❌ **Usage:** `/play <song name or URL>`\n"
            "Example: `/play Nazra Ke Teer`"
        )
        return

    query = " ".join(message.command[1:]) if len(message.command) > 1 else None
    if message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text.strip()

    chat_id = message.chat.id

    # Check auth
    if not await is_auth(message.from_user.id, chat_id) and message.from_user.id != config.OWNER_ID:
        await message.reply("⚠️ You are not authorized to use music commands in this group.")
        return

    status = await message.reply("🔍 **Searching...**")

    track = await extract_info(query, video=False)
    if not track:
        await status.edit("❌ No results found. Try a different query.")
        return

    await add_to_queue(chat_id, {
        "title": track["title"],
        "duration": track["duration"],
        "url": track["url"],
        "webpage_url": track["webpage_url"],
        "uploader": track["uploader"],
        "requested_by": message.from_user.id,
    })

    queue = await get_queue(chat_id)

    if chat_id in active_calls and active_calls[chat_id].get("playing"):
        await status.edit(
            f"✅ **Added to Queue**\n\n"
            f"🎵 **{track['title']}**\n"
            f"⏱ {format_duration(track['duration'])}\n"
            f"📍 Position: #{len(queue)}\n\n"
            f"Use /queue to see the full list.",
            reply_markup=control_keyboard(chat_id),
        )
    else:
        await status.edit("🎧 **Starting playback...**")
        await start_playback(chat_id, message, track)


async def start_playback(chat_id: int, message: Message, track: dict):
    """Start playing a track in the voice chat."""
    try:
        await pytgcalls.join_group_call(
            chat_id,
            AudioPiped(track["url"]),
            stream_type=HighQualityAudio(),
        )
        active_calls[chat_id] = {
            "playing": True,
            "paused": False,
            "current": track,
            "message": message,
        }
        await message.reply(
            f"🎧 **Now Playing**\n\n"
            f"🎵 **{track['title']}**\n"
            f"👤 {track['uploader']}\n"
            f"⏱ {format_duration(track['duration'])}\n\n"
            f"🤖 **{config.BOT_NAME}**",
            reply_markup=control_keyboard(chat_id),
        )
    except Exception as e:
        await message.reply(f"❌ Failed to start playback: `{str(e)}`")


@app.on_message(filters.command("vplay") & filters.group)
async def vplay_cmd(_, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply("❌ **Usage:** `/vplay <song name or URL>`")
        return

    query = " ".join(message.command[1:]) if len(message.command) > 1 else None
    chat_id = message.chat.id

    status = await message.reply("🔍 **Searching video...**")

    track = await extract_info(query, video=True)
    if not track:
        await status.edit("❌ No video results found.")
        return

    if chat_id in active_calls and active_calls[chat_id].get("playing"):
        await add_to_queue(chat_id, {
            "title": track["title"],
            "duration": track["duration"],
            "url": track["url"],
            "webpage_url": track["webpage_url"],
            "uploader": track["uploader"],
            "video": True,
            "requested_by": message.from_user.id,
        })
        await status.edit(f"✅ **Video added to queue:** {track['title']}")
    else:
        try:
            await pytgcalls.join_group_call(
                chat_id,
                AudioVideoPiped(track["url"]),
                stream_type=HighQualityVideo(),
            )
            active_calls[chat_id] = {
                "playing": True,
                "paused": False,
                "current": track,
                "message": message,
                "video": True,
            }
            await message.reply(
                f"📺 **Now Playing (Video)**\n\n"
                f"🎬 **{track['title']}**\n"
                f"👤 {track['uploader']}\n"
                f"⏱ {format_duration(track['duration'])}\n\n"
                f"🤖 **{config.BOT_NAME}**",
                reply_markup=control_keyboard(chat_id),
            )
        except Exception as e:
            await message.reply(f"❌ Failed to start video: `{str(e)}`")


@app.on_message(filters.command("skip") & filters.group)
async def skip_cmd(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in active_calls:
        await message.reply("❌ Nothing is playing.")
        return

    queue = await get_queue(chat_id)
    if queue:
        next_track = queue[0]
        await clear_queue(chat_id)
        for t in queue[1:]:
            await add_to_queue(chat_id, t)
        await start_playback(chat_id, message, next_track)
    else:
        try:
            await pytgcalls.leave_group_call(chat_id)
            del active_calls[chat_id]
            await message.reply("⏭ **Skipped. Queue empty, left voice chat.**")
        except Exception:
            await message.reply("⚠️ Could not leave voice chat.")


@app.on_message(filters.command("stop") & filters.group)
async def stop_cmd(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in active_calls:
        await message.reply("❌ Nothing is playing.")
        return
    try:
        await clear_queue(chat_id)
        await pytgcalls.leave_group_call(chat_id)
        del active_calls[chat_id]
        await message.reply("⏹ **Playback stopped. Left voice chat.**")
    except Exception as e:
        await message.reply(f"⚠️ Error: `{str(e)}`")


@app.on_message(filters.command("pause") & filters.group)
async def pause_cmd(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in active_calls:
        await message.reply("❌ Nothing is playing.")
        return
    try:
        await pytgcalls.pause_stream(chat_id)
        active_calls[chat_id]["paused"] = True
        await message.reply("⏸ **Playback paused.**")
    except Exception as e:
        await message.reply(f"⚠️ Error: `{str(e)}`")


@app.on_message(filters.command("resume") & filters.group)
async def resume_cmd(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in active_calls:
        await message.reply("❌ Nothing is playing.")
        return
    try:
        await pytgcalls.resume_stream(chat_id)
        active_calls[chat_id]["paused"] = False
        await message.reply("▶ **Playback resumed.**")
    except Exception as e:
        await message.reply(f"⚠️ Error: `{str(e)}`")


@app.on_message(filters.command("queue") & filters.group)
async def queue_cmd(_, message: Message):
    chat_id = message.chat.id
    queue = await get_queue(chat_id)
    if not queue and chat_id not in active_calls:
        await message.reply("📋 **Queue is empty.**")
        return

    text = f"📋 **Queue for {config.BOT_NAME}**\n\n"
    if chat_id in active_calls and active_calls[chat_id].get("current"):
        cur = active_calls[chat_id]["current"]
        text += f"🎧 **Now Playing:** {cur['title']}\n"
        text += f"⏱ {format_duration(cur['duration'])}\n\n"
    if queue:
        text += "**Up Next:**\n"
        for i, t in enumerate(queue[:10], 1):
            text += f"{i}. {t['title']} — {format_duration(t['duration'])}\n"
    await message.reply(text)


@app.on_message(filters.command("auth") & filters.group)
async def auth_cmd(_, message: Message):
    if message.from_user.id != config.OWNER_ID:
        await message.reply("⚠️ Only the owner can authorize users.")
        return
    if len(message.command) < 2:
        await message.reply("❌ **Usage:** `/auth <user_id>`")
        return
    target_id = int(message.command[1])
    chat_id = message.chat.id
    await add_auth(target_id, chat_id)
    await message.reply(f"✅ User `{target_id}` authorized in this group.")


@app.on_message(filters.command("playlist") & filters.group)
async def playlist_cmd(_, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    playlist = await get_playlist(user_id)
    if not playlist:
        await message.reply("📭 Your playlist is empty.")
        return
    text = "🎵 **Your Playlist**\n\n"
    for i, t in enumerate(playlist[:20], 1):
        text += f"{i}. {t['title']}\n"
    await message.reply(text)


# ═════════════════════════════════════════════════════════════════════
#  CALLBACK QUERIES (Inline buttons)
# ═════════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^(pause|resume|skip|stop)\|(\d+)$"))
async def control_cb(_, query):
    action = query.matches[0].group(1)
    chat_id = int(query.matches[0].group(2))

    if query.from_user.id != config.OWNER_ID:
        await query.answer("⚠️ Only the owner can control playback.", show_alert=True)
        return

    if chat_id not in active_calls:
        await query.answer("❌ Nothing is playing.", show_alert=True)
        return

    try:
        if action == "pause":
            await pytgcalls.pause_stream(chat_id)
            active_calls[chat_id]["paused"] = True
            await query.answer("⏸ Paused")
        elif action == "resume":
            await pytgcalls.resume_stream(chat_id)
            active_calls[chat_id]["paused"] = False
            await query.answer("▶ Resumed")
        elif action == "skip":
            await query.answer("⏭ Skipping...")
            queue = await get_queue(chat_id)
            if queue:
                next_track = queue[0]
                await clear_queue(chat_id)
                for t in queue[1:]:
                    await add_to_queue(chat_id, t)
                # Create a minimal message-like object for start_playback
                class FakeMsg:
                    chat = type("C", (), {"id": chat_id})()
                    from_user = query.from_user
                await start_playback(chat_id, FakeMsg(), next_track)
            else:
                await pytgcalls.leave_group_call(chat_id)
                if chat_id in active_calls:
                    del active_calls[chat_id]
                await query.edit_message_text("⏹ Queue empty. Left voice chat.")
        elif action == "stop":
            await query.answer("⏹ Stopped")
            await clear_queue(chat_id)
            await pytgcalls.leave_group_call(chat_id)
            if chat_id in active_calls:
                del active_calls[chat_id]
            await query.edit_message_text("⏹ Playback stopped. Left voice chat.")
    except Exception as e:
        await query.answer(f"⚠️ {str(e)}", show_alert=True)


# ═════════════════════════════════════════════════════════════════════
#  STREAM END HANDLER
# ═════════════════════════════════════════════════════════════════════

@pytgcalls.on_stream_end()
async def on_stream_end(_, chat_id: int):
    """Auto-play next track when current ends."""
    queue = await get_queue(chat_id)
    if queue:
        next_track = queue[0]
        await clear_queue(chat_id)
        for t in queue[1:]:
            await add_to_queue(chat_id, t)
        # Find a message-like object to pass
        msg = active_calls.get(chat_id, {}).get("message")
        await start_playback(chat_id, msg, next_track)
    else:
        try:
            await pytgcalls.leave_group_call(chat_id)
        except Exception:
            pass
        if chat_id in active_calls:
            del active_calls[chat_id]


# ═════════════════════════════════════════════════════════════════════
#  STARTUP
# ═════════════════════════════════════════════════════════════════════

async def main():
    config.check()
    await app.start()
    await userbot.start()
    await pytgcalls.start()
    print(f"✅ {config.BOT_NAME} is running!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
        sys.exit(0)
