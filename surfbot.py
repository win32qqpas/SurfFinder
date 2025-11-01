#!/usr/bin/env python3
# main.py — SurfHunter userbot (Telethon) — улучшенная версия
# Динамический мониторинг всех групп, где сидит аккаунт.
# Отправка уведомлений в личку через Bot API.

import os
import sys
import json
import random
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, utils
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, RPCError

# ------------------------
# Конфиг (берём из окружения)
# ------------------------
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")  # Рекомендуется хранить в ENV
BOT_TOKEN = "8438987254:AAHPW6Sq_Z2VmXOEx0DJ7WRWnZ1vfmdi0Ik"  # по просьбе пользователя
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")  # numeric id (куда бот шлёт уведомления)
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "1"))  # пинг-онлайн
HISTORY_CHECK_HOURS = float(os.getenv("HISTORY_CHECK_HOURS", "2"))  # каждые 2 часа проверять историю
HISTORY_CHECK_LIMIT = int(os.getenv("HISTORY_CHECK_LIMIT", "100"))   # 100 сообщений в истории
TZ_OFFSET = int(os.getenv("TZ_OFFSET", "8"))  # Бали = +8
EXCLUDE_CHAT_IDS = os.getenv("EXCLUDE_CHAT_IDS", "")  # опционально: CSV исключённых id
MAX_FORWARDS_PER_HOUR = int(os.getenv("MAX_FORWARDS_PER_HOUR", "40"))  # ограничение пересылаемых уведомлений/час
SEEN_FILE = os.getenv("SEEN_FILE", "seen_ids.json")

# Проверка обязательных переменных
missing = [k for k, v in {
    "API_ID": API_ID, "API_HASH": API_HASH, "SESSION_STRING": SESSION_STRING,
    "OWNER_CHAT_ID": OWNER_CHAT_ID
}.items() if not v]

if missing:
    print("❌ Missing ENV vars:", missing)
    sys.exit(1)

# ------------------------
# Ключевые слова
# ------------------------
KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфингу","сёрфинг","серфингом","сёрфингом",
    "сёрф","серф","инструктор по серфингу","серфурок","уроки серфинга","уроки сёрфинга",
    "сёрфтренер","сёрфкемп","занятия по сёрфингу","тренера по серфингу","тренер по серфингу",
    "серфтренер","занятие по серфингу","серфкемп","ищу инструктора по серфингу","серфуроки",
    "серф инструктор","сёрф тренер","surf","surfing","инструктор для серфинга"
]

# ------------------------
# Временные помощники
# ------------------------
UTC = timezone.utc
def local_now():
    return datetime.now(UTC) + timedelta(hours=TZ_OFFSET)

def local_time_str():
    return local_now().strftime("%H:%M")

def local_datetime_str():
    return local_now().strftime("%d.%m %H:%M")

# ------------------------
# Клиенты
# ------------------------
client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)

BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ------------------------
# Seen messages (анти-дублирование)
# ------------------------
def load_seen():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        return set()
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Error loading seen: {e}")
        return set()

def save_seen(seen_set):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen_set), f, ensure_ascii=False)
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Error saving seen: {e}")

SEEN = load_seen()

def mark_seen(chat_id, msg_id):
    key = f"{chat_id}:{msg_id}"
    if key not in SEEN:
        SEEN.add(key)
        # сохраняем асинхронно, но быстро
        save_seen(SEEN)
        return True
    return False

# ------------------------
# Rate limiter: контролируем количество пересылок за час
# ------------------------
forwards_this_hour = 0
forwards_reset_time = datetime.now(UTC)

def allowed_forward():
    global forwards_this_hour, forwards_reset_time
    now = datetime.now(UTC)
    if now >= forwards_reset_time + timedelta(hours=1):
        forwards_reset_time = now
        forwards_this_hour = 0
    if forwards_this_hour < MAX_FORWARDS_PER_HOUR:
        forwards_this_hour += 1
        return True
    return False

# ------------------------
# Утилиты текста и фильтра
# ------------------------
def contains_keyword(text):
    if not text:
        return False
    t = text.lower()
    for kw in KEYWORDS:
        if kw in t:
            return True
    return False

async def format_message(chat_identifier, msg):
    author = "—"
    try:
        sender = await msg.get_sender()
        if sender:
            author = " ".join(filter(None, [sender.first_name, sender.last_name])) or getattr(sender, "username", "—")
            if getattr(sender, "username", None):
                author += f" (@{sender.username})"
    except Exception:
        pass
    text_snippet = (msg.message[:700] + "...") if len(msg.message or "") > 700 else (msg.message or "")
    link = ""
    ch_name = str(chat_identifier)
    try:
        ent = await client.get_entity(chat_identifier)
        ch_name = ent.username or getattr(ent, "title", str(chat_identifier))
        if getattr(ent, "username", None):
            link = f"https://t.me/{ent.username}/{msg.id}"
    except Exception:
        pass
    header = f"📍 {ch_name}\n👤 {author.strip()}\n🕒 {local_datetime_str()}\n\n"
    body = f"{text_snippet}\n"
    if link:
        body += f"\n🔗 {link}"
    return header + body

# ------------------------
# Отправка через Bot API с бэкоффом и chunking
# ------------------------
async def bot_send_text(text):
    MAX = 3900
    parts = [text[i:i+MAX] for i in range(0, len(text), MAX)]
    async with aiohttp.ClientSession() as session:
        for p in parts:
            # рандомная человеческая пауза перед отправкой
            await asyncio.sleep(random.uniform(0.4, 1.8))
            payload = {"chat_id": int(OWNER_CHAT_ID), "text": p, "disable_web_page_preview": True}
            backoff = 1
            for attempt in range(5):
                try:
                    async with session.post(BOT_API_URL, json=payload, timeout=30) as resp:
                        data = await resp.text()
                        if resp.status == 200:
                            print(f"[{local_time_str()}] 📩 Bot message sent (len {len(p)})")
                            break
                        else:
                            print(f"[{local_time_str()}] ⚠️ Bot API {resp.status}: {data}")
                            # при 429 стоит увеличить backoff
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, 60)
                except Exception as e:
                    print(f"[{local_time_str()}] ⚠️ Error sending bot message: {e}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)

# ------------------------
# Динамическая выборка чатов, где состоит аккаунт
# ------------------------
async def gather_monitored_chats():
    """
    Собирает список dialog id всех групп и каналов, где состоит аккаунт,
    исключая приватные ЛС и сервисные чаты и те, что указаны в EXCLUDE_CHAT_IDS.
    """
    exclude = set()
    if EXCLUDE_CHAT_IDS:
        for s in EXCLUDE_CHAT_IDS.split(","):
            s = s.strip()
            if s:
                try:
                    exclude.add(int(s))
                except:
                    pass

    ids = set()
    async for dialog in client.iter_dialogs():
        try:
            # dialog.entity может быть Channel, Chat, User
            if getattr(dialog, "is_user", False):
                continue  # пропускаем ЛС
            # фильтруем пустые/системные
            ent = dialog.entity
            # Чекаем, что это группа или канал (а не бот/паблик без смысла)
            if getattr(ent, "megagroup", False) or getattr(ent, "broadcast", False) or getattr(ent, "group", False):
                cid = dialog.id
                if cid in exclude:
                    continue
                ids.add(cid)
        except Exception:
            continue
    return ids

# ------------------------
# Проверка истории (один проход для всех monitored chats)
# ------------------------
async def check_history_once(monitored_ids):
    print(f"[{local_time_str()}] 🔎 Проверка истории ({len(monitored_ids)} чатов, limit {HISTORY_CHECK_LIMIT})...")
    found = []
    # Проходим по списку с небольшой рандомной задержкой, чтобы выглядеть «по-человечески»
    for ch in monitored_ids:
        try:
            # читаем небольшими пачками, с рандомной паузой
            msgs = await client.get_messages(ch, limit=HISTORY_CHECK_LIMIT)
            for m in msgs:
                if m.message and contains_keyword(m.message):
                    if mark_seen(ch, m.id):
                        fm = await format_message(ch, m)
                        found.append(fm)
                        # ограничение на скорость формирования — небольшая пауза
                        await asyncio.sleep(random.uniform(0.05, 0.35))
            # пауза между чатами (человеческая)
            await asyncio.sleep(random.uniform(0.8, 1.6))
        except FloodWaitError as e:
            print(f"[{local_time_str()}] ⏳ FloodWait при чтении {ch}: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except RPCError as e:
            print(f"[{local_time_str()}] ⚠️ RPCError чтения {ch}: {e}")
            await asyncio.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"[{local_time_str()}] ⚠️ Ошибка чтения истории {ch}: {e}")
            await asyncio.sleep(random.uniform(1, 3))

    if found:
        batch = "\n\n---\n\n".join(found)
        # если много — разбиваем, и соблюдаем лимиты пересылок в час
        if allowed_forward():
            await bot_send_text(f"🌊 Найдено совпадений в истории ({len(found)}):\n\n{batch}")
            print(f"[{local_time_str()}] ✅ Отправлено найденных сообщений из истории: {len(found)}")
        else:
            print(f"[{local_time_str()}] ⚠️ Превышен лимит пересылок в час, не отправлено {len(found)} найденных сообщений.")
    else:
        print(f"[{local_time_str()}] 😴 Совпадений в истории не найдено.")

# ------------------------
# Обработчик новых сообщений — теперь без фильтра chats=..., но с осторожной фильтрацией внутри.
# ------------------------
@client.on(events.NewMessage)
async def new_message_handler(event):
    try:
        # фильтры — пропускаем личные сообщения (мы мониторим группы/каналы)
        if event.is_private:
            return

        chat_id = event.chat_id
        # небольшая задержка (чтобы не выглядеть молниеносным роботом)
        await asyncio.sleep(random.uniform(0.4, 1.6))

        # некоторые сервисные/админские сообщения лучше пропускать
        # пропускаем, если это сообщение от самого бота или от системных юзеров
        if getattr(event.message, "from_id", None) is None:
            return

        text = event.message.message or ""
        preview = text[:120].replace("\n", " ")
        print(f"[{local_time_str()}] 🆕 Новое сообщение ({chat_id}): {preview}")

        # Проверяем на ключевые слова
        if contains_keyword(text):
            # не форвардим, если лимит пересылок исчерпан
            if not allowed_forward():
                print(f"[{local_time_str()}] ⚠️ Лимит пересылок в час исчерпан — сообщение пропущено.")
                return

            # ставим небольшую рандомную задержку перед обработкой — как человек читает
            await asyncio.sleep(random.uniform(0.4, 2.4))

            # если ранее не отмечено как seen
            if mark_seen(chat_id, event.message.id):
                # формируем и отправляем уведомление ботом
                formatted = await format_message(chat_id, event.message)
                await bot_send_text(formatted)
                print(f"[{local_time_str()}] ✅ Совпадение отправлено.")
            else:
                print(f"[{local_time_str()}] 💤 Уже отмечено как прочитанное — пропускаем.")
    except FloodWaitError as e:
        print(f"[{local_time_str()}] ⏳ FloodWait в handler: {e.seconds}s")
        await asyncio.sleep(e.seconds + 5)
    except Exception as e:
        print(f"[{local_time_str()}] ⚠️ Ошибка в обработчике новых сообщений: {e}")

# ------------------------
# Пинг (каждый час) — чтобы Render не усыплял процесс
# ------------------------
async def periodic_ping():
    while True:
        try:
            # пинг каждые CHECK_INTERVAL_HOURS часов (по умолчанию 1 час)
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
            # рандомим текст пинга — не выглядеть как бот
            pings = [
                f"🏄‍♂️ SurfHunter ONLINE — {local_time_str()}",
                f"🌊 Серф-хантер жив, {local_time_str()}",
                f"🤙 Проверка связи — {local_time_str()} (auto-ping)"
            ]
            await bot_send_text(random.choice(pings))
            print(f"[{local_time_str()}] ⏱️ Пинг отправлен.")
        except Exception as e:
            print(f"[{local_time_str()}] ⚠️ Ошибка при отправке пинга: {e}")
            await asyncio.sleep(10)

# ------------------------
# Периодическая проверка истории (каждые HISTORY_CHECK_HOURS)
# ------------------------
async def periodic_history_check():
    while True:
        try:
            # собираем динамически мониторируемые чаты
            monitored = await gather_monitored_chats()
            # проверяем историю
            await check_history_once(monitored)
        except Exception as e:
            print(f"[{local_time_str()}] ⚠️ Ошибка в периодической проверке истории: {e}")
        # Спим с небольшим джиттером
        await asyncio.sleep(HISTORY_CHECK_HOURS * 3600 + random.uniform(10, 300))

# ------------------------
# Main
# ------------------------
async def main():
    try:
        print(f"[{local_time_str()}] 🚀 Запуск Telethon userbot...")
        await client.start()
        me = await client.get_me()
        display_name = me.first_name or me.username or str(me.id)
        print(f"[{local_time_str()}] ✅ User account started: {display_name}")

        # Стартовое сообщение (отправляем через Bot API)
        start_msg = (
            f"😈 {display_name} - ПОДКЛЮЧЁН К ЭФИРУ ! - {local_time_str()}\n"
            f"🫡 ГОТОВ НЕСТИ МИССИЮ !\n"
            f"🌊 Волны чекаю, все стабильно !\n"
            f"⏱️ Время выхода в АСТРАЛ : {local_datetime_str()}"
        )
        await bot_send_text(start_msg)
        print(f"[{local_time_str()}] 📩 Стартовое уведомление отправлено SurfHanter-ботом.")

        # Первый сбор monitored chats и первая проверка истории
        monitored = await gather_monitored_chats()
        await check_history_once(monitored)

        # Запускаем фоновые задачи
        asyncio.create_task(periodic_ping())
        asyncio.create_task(periodic_history_check())

        # run_until_disconnected() блокирует и обрабатывает события NewMessage
        await client.run_until_disconnected()

    except FloodWaitError as e:
        print(f"[{local_time_str()}] ⏳ FloodWait (main): {e.seconds}s — жду и перезапускаюсь")
        await asyncio.sleep(e.seconds + 5)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        print(f"[{local_time_str()}] 💥 Критическая ошибка (main): {e}")
        # короткая пауза и перезапуск
        await asyncio.sleep(30 + random.uniform(0, 10))
        os.execv(sys.executable, [sys.executable] + sys.argv)

# ------------------------
# Entrypoint
# ------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"[{local_time_str()}] 🛑 Остановка вручную.")
    except Exception as e:
        print(f"[{local_time_str()}] 💥 Unhandled: {e}")