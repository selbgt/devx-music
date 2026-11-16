# 🎵 Dev X Music 🎶

Telegram Group Voice Chat Music Bot — built with **Pyrogram** + **PyTgCalls** + **yt-dlp** + **MongoDB**.

Inspired by AnonXMusic, designed with **Dev X Music 🎶** branding.

## Features

| Command | Description |
|---------|-------------|
| `/play <query\|url>` | Play audio in group voice chat |
| `/vplay <query\|url>` | Play video in group voice chat |
| `/skip` | Skip current track |
| `/stop` | Stop playback & leave voice chat |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/queue` | Show current queue |
| `/playlist` | Show your saved playlist |
| `/auth <user_id>` | Authorize a user (owner only) |
| `/ping` | Ping test |
| `/start` | Welcome message |

## Deploy on Heroku

### One-Click Deploy

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Manual Deploy

```bash
# Clone
git clone https://github.com/selbgt/devx-music.git
cd devx-music

# Create Heroku app
heroku create devx-music

# Add MongoDB addon
heroku addons:create mongolab:sandbox

# Set config vars
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set MONGO_URL=your_mongodb_url
heroku config:set LOGGER_ID=your_logger_id
heroku config:set OWNER_ID=your_owner_id
heroku config:set SESSION=your_pyrogram_session_string
heroku config:set BOT_USERNAME=your_bot_username

# Deploy
git add .
git commit -m "Initial commit"
git push heroku main

# Scale
heroku ps:scale worker=1
```

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_ID` | From my.telegram.org/apps | ✅ |
| `API_HASH` | From my.telegram.org/apps | ✅ |
| `BOT_TOKEN` | From @BotFather | ✅ |
| `MONGO_URL` | From cloud.mongodb.com | ✅ |
| `LOGGER_ID` | Logger group/channel ID | ✅ |
| `OWNER_ID` | Your Telegram user ID | ✅ |
| `SESSION` | Pyrogram session from @StringFatherBot | ✅ |
| `BOT_USERNAME` | Bot username (without @) | ❌ |
| `DURATION_LIMIT` | Max song duration (minutes) | ❌ |
| `QUEUE_LIMIT` | Max queue size | ❌ |

## Local Development

```bash
git clone https://github.com/selbgt/devx-music.git
cd devx-music
pip install -r requirements.txt
cp sample.env .env
# Edit .env with your values
python3 music.py
```

## Project Structure

```
devx-music/
├── music.py          # Main bot entry point
├── config.py         # Configuration
├── requirements.txt  # Python dependencies
├── Procfile          # Heroku process file
├── app.json          # Heroku app manifest
├── sample.env        # Environment template
├── .gitignore        # Git ignore rules
├── README.md         # This file
├── plugins/          # Command plugins
├── core/             # Core functionality
├── helpers/          # Helper utilities
└── locales/          # Language strings
```

## Support

- 📢 Channel: https://t.me/DevXMusic
- 💬 Chat: https://t.me/DevXMusicChat
- 👤 Owner: [Telegram User](tg://user?id=OWNER_ID)

Built with ❤️ by **Dev X Music 🎶**
