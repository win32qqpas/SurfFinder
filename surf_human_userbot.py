#!/usr/bin/env python3
# 🌊 SurfHuman Userbot — мониторинг Telegram по ключевым словам (серфинг, обучение и т.п.)

import os
import sys
import json
import asyncio
import aiohttp
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# =========================
# 🔧 Настройки окружения
# =========================

def clean_env(varname: str, required: bool = True) -> str:
    """Безопасно читает переменные окружения и очищает от лишних символов."""
    val = os.getenv(varname)
    if val:
        val = val.strip().replace("\n", "").replace("\r", "")
    if required and not val:
        print(f"❌ ENV переменная {varname} отсутствует или пуста")
    return val or ""

API_ID = clean_env("API_ID")
API_HASH = clean_env("API_HASH")
SESSION_STRING = clean_env("SESSION_STRING")
BOT_TOKEN = clean_env("BOT_TOKEN")
OWNER_CHAT_ID = clean_env("OWNER_CHAT_ID")
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "2").strip())
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "8").strip())  # Бали по умолчанию

# 📋 Проверка окружения
missing = [k for k, v in {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "SESSION_STRING": SESSION_STRING,
    "BOT_TOKEN": BOT_TOKEN,
    "OWNER_CHAT_ID": OWNER_CHAT_ID
}.items() if not v]

if missing:
    print("❌ Отсутствуют ENV переменные:", missing)
    sys.exit(1)

print("🔍 DEBUG Render environment:")
for key in ["API_ID", "API_HASH", "SESSION_STRING", "BOT_TOKEN", "OWNER_CHAT_ID"]:
    val = os.getenv(key)
    print(f"  {key}: {'✅ set' if val else '❌ missing'} (len={len(val) if val else 0})")

# =========================
# 🌊 Ключевые слова
# =========================
KEYWORDS = [
    "серфинг", "сёрфинг", "серф", "сёрф", "surf", "surfing",
    "инструктор по серфингу", "уроки серфинга", "сёрфтренер",
    "серфкемп", "занятие по серфингу", "тренер по серфингу",
    "инструктор для серфинга", "сёрф кемп", "серф лагерь", "surf school"
]

# =========================
# 🕒 Время и формат
# =========================
def local_now():
    return datetime.now(timezone.utc) + timedelta(hours=TZ_OFFSET)

def local_time():
    return local_now().strftime("%H:%M")

def local_datetime():
    return local_now().strftime("%d.%m %H:%M")

# =========================
# 🧠 Работа с seen-файлом
# =========================
SEEN_FILE = "seen_msgs.json"

def load_seen():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()

def save_seen(data):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(data), f, ensure_ascii=False)
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка сохранения seen: {e}")

SEEN = load_seen()

# =========================
# ⚙️ Telethon Client
# =========================
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

# =========================
# 📬 Отправка сообщений через Bot API
# =========================
async def bot_send(text):
    if not text:
        return
    MAX = 3900
    parts = [text[i:i+MAX] for i in range(0, len(text), MAX)]
    async with aiohttp.ClientSession() as session:
        for p in parts:
            try:
                async with session.post(BOT_API_URL, json={
                    "chat_id": int(OWNER_CHAT_ID),
                    "text": p,
                    "disable_web_page_preview": True
                }) as r:
                    print(f"[{local_time()}] 📩 Сообщение отправлено ({r.status})")
            except Exception as e:
                print(f"[{local_time()}] ⚠️ Ошибка отправки Bot API: {e}")

# =========================
# 🔎 Поиск по ключевым словам
# =========================
def contains_keyword(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

def mark_seen(chat_id, msg_id):
    key = f"{chat_id}:{msg_id}"
    if key not in SEEN:
        SEEN.add(key)
        save_seen(SEEN)
        return True
    return False

# =========================
# 🧾 Форматирование найденных сообщений
# =========================
async def format_msg(event):
    try:
        sender = await event.get_sender()
        author = " ".join(filter(None, [sender.first_name, sender.last_name])) or getattr(sender, "username", "—")
        if getattr(sender, "username", None):
            author += f" (@{sender.username})"
    except Exception:
        author = "—"

    chat = await event.get_chat()
    ch_name = getattr(chat, "title", "—")
    link = ""
    if getattr(chat, "username", None):
        link = f"https://t.me/{chat.username}/{event.message.id}"

    msg_text = event.message.message or ""
    if len(msg_text) > 700:
        msg_text = msg_text[:700] + "..."

    text = f"📍 {ch_name}\n👤 {author}\n🕒 {local_datetime()}\n\n{msg_text}"
    if link:
        text += f"\n🔗 {link}"
    return text

# =========================
# ⚡ Обработка новых сообщений
# =========================
@client.on(events.NewMessage)
async def handler(event):
    if not (event.is_group or event.is_channel):
        return
    msg = event.message.message
    if contains_keyword(msg):
        if mark_seen(event.chat_id, event.message.id):
            await asyncio.sleep(random.uniform(0.5, 2.0))
            fm = await format_msg(event)
            await bot_send(fm)
            print(f"[{local_time()}] ✅ Новое совпадение: {event.chat_id}")

# =========================
# 🕵️ Проверка истории
# =========================
async def check_history():
    print(f"[{local_time()}] 🔍 Проверка истории чатов...")
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
        try:
            msgs = await client.get_messages(dialog.id, limit=100)
            for m in msgs:
                if m.message and contains_keyword(m.message):
                    if mark_seen(dialog.id, m.id):
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        fake_event = type("Ev", (), {"message": m, "get_sender": m.get_sender, "get_chat": m.get_chat})
                        fm = await format_msg(fake_event)
                        await bot_send(fm)
            await asyncio.sleep(random.uniform(1.5, 3.0))
        except FloodWaitError as e:
            print(f"[{local_time()}] ⏳ FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка при проверке истории: {e}")

# =========================
# 👁️ Имитация активности
# =========================
async def random_activity():
    while True:
        try:
            choice = random.choice(["sleep", "active", "idle"])
            if choice == "active":
                dialogs = await client.get_dialogs(limit=1)
                if dialogs:
                    await client.send_read_acknowledge(dialogs[0])
                print(f"[{local_time()}] 👁️ Имитация активности (read)")
            elif choice == "idle":
                await asyncio.sleep(random.uniform(20, 60))
            await asyncio.sleep(random.uniform(60, 180))
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка активности: {e}")

# =========================
# ⏱️ Пинг для проверки живости
# =========================
async def periodic_ping():
    while True:
        try:
            await bot_send(f"🏄‍♂️ SurfHunter активен — {local_time()}")
            print(f"[{local_time()}] ⏱️ Пинг отправлен.")
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка пинга: {e}")
            await asyncio.sleep(600)

# =========================
# 🚀 Основной цикл
# =========================
async def main():
    print(f"[{local_time()}] 🚀 Запуск SurfHuman userbot...")
    await client.start()
    me = await client.get_me()
    print(f"[{local_time()}] ✅ Аккаунт {me.first_name or me.username} запущен!")

    await bot_send(f"🌊 Userbot подключен к эфиру {local_datetime()}\n🤙 SurfHunter готов.")

    asyncio.create_task(periodic_ping())
    asyncio.create_task(random_activity())

    while True:
        try:
            await check_history()
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        except Exception as e:
            print(f"[{local_time()}] 💥 Ошибка цикла: {e}")
            await asyncio.sleep(60)

# =========================
# ▶️ Entrypoint
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"[{local_time()}] 🛑 Остановка вручную.")
    except Exception as e:
        print(f"[{local_time()}] 💥 Ошибка при запуске: {e}")