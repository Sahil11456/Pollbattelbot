# ⚔️ Telegram Poll Battle Bot v22.4.0-PRO

A high-performance, asynchronous Telegram bot built with **python-telegram-bot v22+**, **aiosqlite**, and **SQLite3**. Designed for viral poll contests, live voting battles, channel integration, and community engagement.

---

## 🌟 Key Features

- ⚡ **Asynchronous SQLite (aiosqlite)** with query indexing & foreign key integrity
- 📊 **Poll Battles**: Public, Anonymous, & Quiz Modes with Single/Multiple choice
- 🏆 **Global Leaderboard & Achievement Badges**
- 🔥 **Trending & Hot Score Velocity Engine**
- 🛡️ **Full Admin Control Panel** with global broadcasts & user ban management
- 📢 **Channel Integration & Force-Join Membership Validation**
- 🚀 **1-Click Railway / Render / Termux / VPS Deployment**

---

## 🛠️ Quick Installation & Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/poll-battle-bot.git
cd poll-battle-bot

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your Telegram BOT_TOKEN and ADMIN_IDS

# 4. Launch Bot
python bot.py
```

---

## 🚀 Deployment Platforms

- **Railway**: Connect repo, set `BOT_TOKEN`, deployment automatic via Nixpacks.
- **Render**: Create background worker, command: `python bot.py`.
- **VPS / Docker**: Use supplied `Dockerfile` or systemd service.
