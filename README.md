# 🛡️ InkMind Group Moderator Bot

> A professional, AI-powered Telegram group moderator designed to keep community spaces clean, respectful, and organized. Built specifically for the InkMind ecosystem and large professional communities.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.0+-green.svg)
![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)

---

## ✨ Features
- **AI-Powered Toxicity Filtering**: Uses Google's Gemini LLM to analyze message context and seamlessly delete toxic, hateful, or inappropriate content.
- **Banned Keyword Filtering**: Instantly removes obvious spam or scam links.
- **Automated Welcomes**: Professionally greets new members when they join the group.
- **Command Management**: Provides `/rules` and `/start` commands for community onboarding.
- **Admin Bypass**: Automatically respects group hierarchy, allowing admins to bypass moderation filters.

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher.
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).
- A Google Gemini API Key.

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/tricks-ter/inkmind-moderator-bot.git
cd inkmind-moderator-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit the `.env` file and insert your API keys:
```env
TELEGRAM_TOKEN=your_telegram_bot_token_from_botfather
GEMINI_API_KEY=your_google_gemini_api_key
```

### 4. Running the Bot
```bash
python bot.py
```

---

## 🤖 Usage
1. Add the bot to your Telegram Supergroup.
2. Promote the bot to an **Administrator** with permissions to *Delete Messages*.
3. Members can type `/rules` to see the group guidelines.
4. The bot will quietly run in the background, keeping your exhibition space safe!

## 📄 License
MIT License
