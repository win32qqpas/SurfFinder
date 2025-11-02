#!/usr/bin/env python3
# 🌊 SurfHuman Userbot — мониторинг Telegram по ключевым словам (серфинг, обучение и т.п.)

import os
import sys
import json
import asyncio
import aiohttp
import random
import atexit
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
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "8").strip())
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "8").strip())  # Бали по умолчанию

# =========================
# 📋 Проверка окружения
# =========================

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

BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

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
# 🧠 Seen-файл
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
# 🔎 Проверка ключевых слов
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
# 🧾 Форматирование сообщений
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
# 💬 Настройки поведения
# =========================
REACTION_DELAY_MIN = float(os.getenv("REACTION_DELAY_MIN", "4.0"))
REACTION_DELAY_MAX = float(os.getenv("REACTION_DELAY_MAX", "10.0"))
SEND_DELAY_MIN = float(os.getenv("SEND_DELAY_MIN", "2.0"))
SEND_DELAY_MAX = float(os.getenv("SEND_DELAY_MAX", "8.0"))
PER_CHAT_COOLDOWN_SECONDS = int(os.getenv("PER_CHAT_COOLDOWN_SECONDS", "900"))  # 15 мин
GLOBAL_RATE_WINDOW = int(os.getenv("GLOBAL_RATE_WINDOW", "600"))  # 10 мин
GLOBAL_RATE_MAX = int(os.getenv("GLOBAL_RATE_MAX", "6"))

_last_sent_per_chat = {}
_global_sent_times = []
_pending_per_chat = {}

# =========================
# ⚡ Обработка новых сообщений
# =========================
@client.on(events.NewMessage)
async def handler(event):
    try:
        if not (event.is_group or event.is_channel):
            return
        msg = event.message.message
        if not msg or not contains_keyword(msg):
            return

        chat_id = event.chat_id
        msg_id = event.message.id

        if not mark_seen(chat_id, msg_id):
            return

        now_ts = asyncio.get_event_loop().time()
        last = _last_sent_per_chat.get(chat_id, 0)
        if now_ts - last < PER_CHAT_COOLDOWN_SECONDS:
            lst = _pending_per_chat.setdefault(chat_id, [])
            lst.append((msg_id, await format_msg(event)))
            print(f"[{local_time()}] ⏳ В cooldown для чата {chat_id}, отложено ({len(lst)})")
            return

        await asyncio.sleep(random.uniform(REACTION_DELAY_MIN, REACTION_DELAY_MAX))
        fm = await format_msg(event)
        await asyncio.sleep(random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX))

        cutoff = now_ts - GLOBAL_RATE_WINDOW
        while _global_sent_times and _global_sent_times[0] < cutoff:
            _global_sent_times.pop(0)
        if len(_global_sent_times) >= GLOBAL_RATE_MAX:
            _pending_per_chat.setdefault(chat_id, []).append((msg_id, fm))
            print(f"[{local_time()}] 🚫 Глобальный rate-limit, отложено.")
            return

        await bot_send(fm)
        _global_sent_times.append(now_ts)
        _last_sent_per_chat[chat_id] = now_ts
        print(f"[{local_time()}] ✅ Уведомление отправлено по чату {chat_id}")

    except FloodWaitError as e:
        print(f"[{local_time()}] ⏳ FloodWait: {e.seconds}s")
        await asyncio.sleep(e.seconds + random.uniform(2, 6))
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка в handler: {e}")

# =========================
# 🔁 Проверка истории
# =========================
async def check_history():
    print(f"[{local_time()}] 🔍 Проверка истории чатов...")
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
        try:
            msgs = await client.get_messages(dialog.id, limit=60)
            for m in msgs:
                if m.message and contains_keyword(m.message):
                    if mark_seen(dialog.id, m.id):
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        fake_event = type("Ev", (), {"message": m, "get_sender": m.get_sender, "get_chat": m.get_chat})
                        fm = await format_msg(fake_event)
                        await bot_send(fm)
            await asyncio.sleep(random.uniform(2, 4))
        except FloodWaitError as e:
            print(f"[{local_time()}] ⏳ FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка check_history: {e}")

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
# ⏳ Отложенные уведомления
# =========================
async def pending_watcher():
    while True:
        try:
            now_ts = asyncio.get_event_loop().time()
            for chat_id in list(_pending_per_chat.keys()):
                last = _last_sent_per_chat.get(chat_id, 0)
                if now_ts - last >= PER_CHAT_COOLDOWN_SECONDS:
                    pending = _pending_per_chat.pop(chat_id, [])
                    if not pending:
                        continue
                    parts = [p for _, p in pending[:3]]
                    agg = "🔔 Отложенные упоминания:\n\n" + "\n\n".join(parts)
                    cutoff = now_ts - GLOBAL_RATE_WINDOW
                    while _global_sent_times and _global_sent_times[0] < cutoff:
                        _global_sent_times.pop(0)
                    if len(_global_sent_times) >= GLOBAL_RATE_MAX:
                        _pending_per_chat.setdefault(chat_id, []).extend(pending)
                        continue
                    await asyncio.sleep(random.uniform(2, 6))
                    await bot_send(agg)
                    _global_sent_times.append(asyncio.get_event_loop().time())
                    _last_sent_per_chat[chat_id] = asyncio.get_event_loop().time()
                    print(f"[{local_time()}] ✅ Отправлен агрегат для {chat_id}")
            await asyncio.sleep(45 + random.uniform(0, 30))
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка pending_watcher: {e}")
            await asyncio.sleep(10)

# =========================
# ⏱️ Пинг
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
# 🧱 Анти-дубликат
# =========================
LOCK_FILE = "/tmp/surfhuman.lock"
def ensure_single_instance():
    if os.path.exists(LOCK_FILE):
        print(f"[{local_time()}] ⚠️ SurfHuman уже запущен — второй экземпляр остановлен.")
        sys.exit(0)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))

# =========================
# 🚀 Основной цикл
# =========================
async def main():
    ensure_single_instance()
    print(f"[{local_time()}] 🚀 Запуск SurfHuman userbot...")

    await client.start()
    await client.connect()
    if not await client.is_user_authorized():
        msg = "❌ SESSION_STRING недействителен или устарел. Обнови его в Render Environment."
        print(f"[{local_time()}] {msg}")
        try:
            await bot_send(msg)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка уведомления: {e}")
        await asyncio.sleep(600)
        sys.exit(1)

    me = await client.get_me()
    print(f"[{local_time()}] ✅ Аккаунт {me.first_name or me.username} запущен!")
    await asyncio.sleep(random.uniform(2, 5))
    await bot_send(f"🌊 Userbot подключен к эфиру {local_datetime()}\n🤙 SurfHunter готов.")

    asyncio.create_task(periodic_ping())
    asyncio.create_task(random_activity())
    asyncio.create_task(pending_watcher())

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