# 🏆 Telegram Poll Battle Bot

A high-performance, fully production-ready, async-driven **Telegram Poll Battle Bot** designed with Python 3.12+, `python-telegram-bot v22+`, and `aiosqlite` SQLite storage engines. This bot facilitates highly customizable voting channels, Arena battles, experience progression tracking, and rigid anti-spam security shields.

---

## ✨ Features Breakdown

### 🗳️ Core Poll Management
* **Aesthetic Wizards**: Step-by-step interactive configuration of poll titles, descriptions, options, and duration limits.
* **Smart Results Display**: Dynamic, high-resolution unicode progress bars matching actual option distributions.
* **Double-Vote Protection**: Rigid transaction-level UNIQUE constraints prevent duplicate records.

### 🎮 Gamification Progression
* **XP Milestones**: +10 XP awarded per cast vote, +25 XP awarded for poll creators.
* **Rankings/Levels**: Climb levels (every 100 XP) to unlock exclusive ranks and title banners.
* **Personal Profile**: Interactive cards detailing achievements, experience ratios, and historic metrics.

### 📊 Deep System Analytics
* **Visual Charts**: Generates customized distribution bar charts using `matplotlib` and transmits them as rich media payloads.
* **Global Dashboards**: High-speed SQL queries compile real-time metrics including total votes, user counts, and query hit-ratios.

### 🛡️ Multi-Layer Security
* **Force-Join verification**: Constrains user action parameters (voting, searching, creation) until they subscribe to required channels.
* **Unique Device Token Verification**: Requires device token registry checks before confirming votes.
* **Rate-Limiters**: Integrates an anti-flood click limiter (600ms) with a 3-second temporary system block.
* **Access Ban-Lists**: Allows admins to restrict bad actors instantly.

### 👨‍💼 Admin Operations Deck
* **Interactive Control Deck**: Interactive dashboards for backup, recovery, rebooting daemon, and diagnostic logs.
* **Announcement Broadcaster**: Send plain text messages, photo media, forward posts, or yes/no button queries to all registered users.

---

## 🛠️ Installation & Execution

### 1. Configure Secrets
Clone this directory, create `.env` file (refer `.env.example`), and set your variables:
```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
ADMIN_IDS=YOUR_TELEGRAM_ID
REQUIRED_CHANNEL=@YourChannel
