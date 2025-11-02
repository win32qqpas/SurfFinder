#!/usr/bin/env python3
# surf_human_userbot — монитор чатов с "человеческим" поведением

import os
import sys
import json
import asyncio
import aiohttp
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, RPCError

# =========================
# 🔧 Настройки окружения
# =========================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")  # сессия твоего аккаунта
BOT_TOKEN = "8438987254:AAHPW6Sq_Z2VmXOEx0DJ7WRWnZ1vfmdi0Ik"
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")  # numeric id (твоя личка)
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "2"))
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "8"))  # Бали

# Проверка окружения
missing = [k for k, v in {"API_ID": API_ID, "API_HASH": API_HASH, "SESSION_STRING": SESSION_STRING, "OWNER_CHAT_ID": OWNER_CHAT_ID}.items() if not v]
if missing:
    print("❌ Отсутствуют ENV переменные:", missing)
    sys.exit(1)

# =========================
# 🌊 Ключевые слова
# =========================
KEYWORDS = [
    "серфинг","сёрфинг","серф","сёрф","surf","surfing",
    "инструктор по серфингу","уроки серфинга","сёрфтренер",
    "серфкемп","занятие по серфингу","тренер по серфингу",
    "инструктор для серфинга","сёрф кемп","серф лагерь","surf school"
]

# =========================
# 🕒 Время
# =========================
UTC = timezone.utc
def local_now():
    return datetime.now(UTC) + timedelta(hours=TZ_OFFSET)
def local_time():
    return local_now().strftime("%H:%M")
def local_datetime():
    return local_now().strftime("%d.%m %H:%M")

# =========================
# 🧠 Файлы
# =========================
SEEN_FILE = "seen_msgs.json"

def load_seen():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_seen(data):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(data), f, ensure_ascii=False)
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка сохранения: {e}")

SEEN = load_seen()

# =========================
# 🧩 Telethon client
# =========================
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)
BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# =========================
# 📬 Отправка через Bot API
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
                    print(f"[{local_time()}] 📩 Сообщение отправлено (len {len(p)}) — {r.status}")
            except Exception as e:
                print(f"[{local_time()}] ⚠️ Ошибка Bot API: {e}")

# =========================
# 🕵️‍♂️ Keyword checker
# =========================
def contains_keyword(text):
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
# 🧾 Форматирование сообщений
# =========================
async def format_msg(event):
    try:
        sender = await event.get_sender()
        author = " ".join(filter(None, [sender.first_name, sender.last_name])) or getattr(sender, "username", "—")
        if getattr(sender, "username", None):
            author += f" (@{sender.username})"
    except:
        author = "—"

    chat = await event.get_chat()
    ch_name = getattr(chat, "title", "—")
    link = ""
    if getattr(chat, "username", None):
        link = f"https://t.me/{chat.username}/{event.message.id}"

    msg_text = event.message.message or ""
    if len(msg_text) > 700:
        msg_text = msg_text[:700] + "..."

    text = (
        f"📍 {ch_name}\n👤 {author}\n🕒 {local_datetime()}\n\n"
        f"{msg_text}\n"
    )
    if link:
        text += f"🔗 {link}"
    return text

# =========================
# 🔎 Проверка истории
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
                        fake_pause()
                        fm = await format_msg(type("Ev", (), {"message": m, "get_sender": m.get_sender, "get_chat": m.get_chat}))
                        await bot_send(fm)
            await asyncio.sleep(random.uniform(1.5, 3.0))
        except FloodWaitError as e:
            print(f"[{local_time()}] ⏳ FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка истории: {e}")

# =========================
# ⚡ Обработка новых сообщений
# =========================
@client.on(events.NewMessage)
async def handler(event):
    if not (event.is_group or event.is_channel):
        return
    if not event.message.message:
        return
    text = event.message.message
    if contains_keyword(text):
        if mark_seen(event.chat_id, event.message.id):
            fake_pause()
            fm = await format_msg(event)
            await bot_send(fm)
            print(f"[{local_time()}] ✅ Найдено совпадение в {event.chat_id}")

# =========================
# 🧍‍♂️ Имитация живого аккаунта
# =========================
async def random_activity():
    while True:
        try:
            # случайно имитируем "чтение", "в онлайне" или "ничего"
            choice = random.choice(["sleep", "active", "idle"])
            if choice == "active":
                await client.send_read_acknowledge(await client.get_dialogs(limit=1))
                print(f"[{local_time()}] 👁️ Имитация активности (read)")
            elif choice == "idle":
                await asyncio.sleep(random.uniform(20, 60))
            await asyncio.sleep(random.uniform(60, 180))
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка активности: {e}")

def fake_pause():
    """Добавляет случайные мини-задержки для имитации человеческих действий"""
    asyncio.sleep(random.uniform(0.5, 2.5))

# =========================
# 🏄 Периодический пинг
# =========================
async def periodic_ping():
    while True:
        try:
            await bot_send(f"🏄‍♂️ SurfHunter активен — {local_time()}")
            print(f"[{local_time()}] ⏱️ Пинг отправлен.")
            await asyncio.sleep(3600)  # каждый час
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка пинга: {e}")
            await asyncio.sleep(600)

# =========================
# 🚀 Main
# =========================
async def main():
    print(f"[{local_time()}] 🚀 Запуск userbot...")
    await client.start()
    me = await client.get_me()
    print(f"[{local_time()}] ✅ Аккаунт {me.first_name or me.username} запущен!")

    await bot_send(f"🌊 Userbot подключен к эфиру! {local_datetime()}\n🤙 SurfHunter готов.")
    asyncio.create_task(periodic_ping())
    asyncio.create_task(random_activity())

    while True:
        try:
            await check_history()
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        except Exception as e:
            print(f"[{local_time()}] 💥 Ошибка в цикле: {e}")
            await asyncio.sleep(60)
            os.execv(sys.executable, [sys.executable] + sys.argv)

# =========================
# ⏯️ Entrypoint
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"[{local_time()}] 🛑 Остановка вручную.")
    except Exception as e:
        print(f"[{local_time()}] 💥 Ошибка при запуске: {e}")
