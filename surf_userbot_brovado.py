#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ------------------------
# ENV
# ------------------------
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "1"))
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "8"))

# Проверка env
missing = [k for k, v in {
    "API_ID": API_ID, "API_HASH": API_HASH,
    "SESSION_STRING": SESSION_STRING, "BOT_TOKEN": BOT_TOKEN,
    "OWNER_CHAT_ID": OWNER_CHAT_ID
}.items() if not v]

if missing:
    print("❌ Missing ENV vars:", missing)
    sys.exit(1)

# ------------------------
# Чаты и ключевые слова
# ------------------------
CHAT_IDS = [
    -1001356532108, -1002363500314, -1001311121622, -1001388027785,
    -1001508876175, -1001277376699, -1001946343717, -1001341855810,
    -1001278212382, -1001361144761, -1001706773923, -1001643118953,
    -1001032422089, -1001716678830, -1001540608753, -1001867725040,
    -1001726137174, -1002624129997, -1002490371800
]

KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфингу","сёрфинг","серфингом","сёрфингом",
    "сёрф","серф","инструктор по серфингу","серфурок","уроки серфинга","уроки сёрфинга",
    "сёрфтренер","сёрфкемп","занятия по сёрфингу","тренера по серфингу","тренер по серфингу",
    "серфтренер","занятие по серфингу","серфкемп","ищу инструктора по серфингу","серфуроки",
    "инструктор","инструкторсерф","surf","surfing","инструкторсерфинга"
]

HISTORY_CHECK_LIMIT = 100
SEEN_FILE = "seen_ids.json"

# ------------------------
# Временные функции
# ------------------------
UTC = timezone.utc
def local_now(): return datetime.now(UTC) + timedelta(hours=TZ_OFFSET)
def local_time_str(): return local_now().strftime("%H:%M")
def local_datetime_str(): return local_now().strftime("%d.%m %H:%M")

# ------------------------
# Telethon клиент
# ------------------------
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)
BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

async def bot_send_text(text):
    MAX = 3900
    parts = [text[i:i+MAX] for i in range(0, len(text), MAX)]
    async with aiohttp.ClientSession() as session:
        for p in parts:
            payload = {"chat_id": int(OWNER_CHAT_ID), "text": p, "disable_web_page_preview": True}
            try:
                async with session.post(BOT_API_URL, json=payload, timeout=30) as resp:
                    data = await resp.text()
                    if resp.status != 200:
                        print(f"[{local_time_str()}] ⚠️ Bot API {resp.status}: {data}")
                    else:
                        print(f"[{local_time_str()}] 📩 Bot message sent (len {len(p)})")
            except Exception as e:
                print(f"[{local_time_str()}] ⚠️ Error sending bot message: {e}")

# ------------------------
# Seen
# ------------------------
def load_seen():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        return set()
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Error load seen file: {e}")
        return set()

def save_seen(seen_set):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen_set), f, ensure_ascii=False)
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Error save seen file: {e}")

SEEN = load_seen()
def mark_seen(chat_id, msg_id):
    key = f"{chat_id}:{msg_id}"
    if key not in SEEN:
        SEEN.add(key)
        save_seen(SEEN)
        return True
    return False

def contains_keyword(text):
    if not text: return False
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

async def format_message(chat_identifier, msg):
    author = "—"
    try:
        sender = await msg.get_sender()
        if sender:
            author = " ".join(filter(None,[sender.first_name,sender.last_name])) or getattr(sender,"username","—")
            if getattr(sender,"username",None): author += f" (@{sender.username})"
    except Exception: pass
    text_snippet = (msg.message[:700] + "...") if len(msg.message or "") > 700 else (msg.message or "")
    link=""
    try:
        ent = await client.get_entity(chat_identifier)
        ch_name = ent.username or getattr(ent,"title",str(chat_identifier))
        if getattr(ent,"username",None): link=f"https://t.me/{ent.username}/{msg.id}"
    except Exception: ch_name=str(chat_identifier)
    return f"📍 {ch_name}\n👤 {author}\n🕒 {local_datetime_str()}\n\n{text_snippet}\n{('🔗 '+link) if link else ''}"

# ------------------------
# Проверка истории
# ------------------------
async def check_history_and_send():
    found=[]
    for ch in CHAT_IDS:
        try:
            msgs = await client.get_messages(ch, limit=HISTORY_CHECK_LIMIT)
            for m in msgs:
                if m.message and contains_keyword(m.message) and mark_seen(ch,m.id):
                    fm = await format_message(ch,m)
                    found.append(fm)
            await asyncio.sleep(1.1)
        except FloodWaitError as e:
            print(f"[{local_time_str()}] ⏳ FloodWait {ch}: {e.seconds}s")
            await asyncio.sleep(e.seconds+5)
        except Exception as e: print(f"[{local_time_str()}] ⚠️ Ошибка истории {ch}: {e}")
    if found:
        batch="\n\n---\n\n".join(found)
        await bot_send_text(f"🌊 Найдено совпадений в истории ({len(found)}):\n\n{batch}")
        print(f"[{local_time_str()}] ✅ История обработана.")
    else: print(f"[{local_time_str()}] 😴 Совпадений нет.")

# ------------------------
# Новые сообщения
# ------------------------
@client.on(events.NewMessage(chats=CHAT_IDS))
async def new_message_handler(event):
    try:
        text=event.message.message or ""
        chat_id=event.chat_id
        preview=text[:120].replace("\n"," ")
        print(f"[{local_time_str()}] 🆕 Новое ({chat_id}): {preview}")
        if contains_keyword(text) and mark_seen(chat_id,event.message.id):
            formatted=await format_message(chat_id,event.message)
            await bot_send_text(formatted)
            print(f"[{local_time_str()}] ✅ Совпадение отправлено.")
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Ошибка в обработчике: {e}")

# ------------------------
# Пинг
# ------------------------
async def periodic_ping():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_HOURS*3600)
        try: 
            await bot_send_text(f"🏄‍♂️ SurfHunter ONLINE — {local_time_str()}")
            print(f"[{local_time_str()}] ⏱️ Пинг отправлен.")
        except Exception as e: 
            print(f"[{local_time_str()}] ⚠️ Ошибка пинга: {e}")

# ------------------------
# Main
# ------------------------
async def main():
    try:
        await client.start()
        me=await client.get_me()
        display_name=me.first_name or me.username or str(me.id)
        print(f"[{local_time_str()}] ✅ User started: {display_name}")
        await bot_send_text(f"😈 {display_name} подключён — {local_time_str()}")
        await check_history_and_send()
        asyncio.create_task(periodic_ping())
        await client.run_until_disconnected()
    except FloodWaitError as e:
        print(f"[{local_time_str()}] ⏳ FloodWait main: {e.seconds}s")
        await asyncio.sleep(e.seconds+5)
        os.execv(sys.executable,[sys.executable]+sys.argv)
    except Exception as e:
        print(f"[{local_time_str()}] 💥 Ошибка main: {e}")
        await asyncio.sleep(60)
        os.execv(sys.executable,[sys.executable]+sys.argv)

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print(f"[{local_time_str()}] 🛑 Stopped manually.")