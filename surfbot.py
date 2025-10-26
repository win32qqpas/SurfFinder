import os
import asyncio
import random
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from datetime import datetime, timezone

# =============================
# Переменные окружения
# =============================
SESSION_STRING = os.environ.get("SESSION_STRING")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 0.75))

if not SESSION_STRING:
    raise SystemExit("ERROR: SESSION_STRING не задан. Сгенерируй её через make_session.py и добавь в Environment Variables.")
if not API_ID or not API_HASH:
    raise SystemExit("ERROR: API_ID или API_HASH не заданы. Добавь их в Environment Variables.")

print("✅ SESSION_STRING видна, первые 10 символов:", SESSION_STRING[:10])

# =============================
# Каналы и ключевые слова
# =============================
CHANNELS = [
    "balichatik","voprosBali","bali_russia_choogl","cangguchat",
    "bali_ubud_changu","balichat_canggu","balichat_bukit","balichatnash",
    "balichat_bukitwoman","balichatfit","balichatsurfing","balisurfer",
    "ChatCanggu","bukit_bali2","baliaab666","bali_chat","bali_ua"
]

KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфингу","сёрфинг","серфингом","сёрфингом","сёрф","серф",
    "инструктор по серфингу","серфурок","уроки серфинга","уроки сёрфинга","сёрфтренер","сёрфкемп",
    "занятия по сёрфингу","тренера по серфингу","тренер по серфингу","серфтренер","занятие по серфингу",
    "серфкемп","ищу инструктора по серфингу"
]

# =============================
# Инициализация клиента
# =============================
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

# =============================
# Вспомогательные функции
# =============================
def contains_keyword(text):
    text = text.lower()
    return any(kw.lower() in text for kw in KEYWORDS)

async def format_message(channel, msg):
    author = "—"
    try:
        sender = await msg.get_sender()
        if sender:
            author = (sender.first_name or "") + " " + (sender.last_name or "")
            if getattr(sender, "username", None):
                author += f" (@{sender.username})"
    except Exception:
        pass
    text_snippet = (msg.message[:700] + "...") if len(msg.message or "") > 700 else (msg.message or "")
    link = f"https://t.me/{channel}/{msg.id}" if getattr(msg, "id", None) else f"https://t.me/{getattr(msg.to_id, 'channel_id', '')}"
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {msg.date.strftime('%d.%m %H:%