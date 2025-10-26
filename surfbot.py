import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# =============================
# Локальное время (GMT+8 — Бали)
# =============================
TZ_OFFSET = 8  # часы (Бали)

def local_time():
    return (datetime.now(timezone.utc) + timedelta(hours=TZ_OFFSET)).strftime('%H:%M')

def local_datetime():
    return (datetime.now(timezone.utc) + timedelta(hours=TZ_OFFSET)).strftime('%d.%m %H:%M')

# =============================
# Переменные окружения (Render)
# =============================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # твой личный ID (куда бот шлёт уведомления)
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "1").strip())

print("\n🔍 Проверяем переменные окружения:\n")
print(f"API_ID = {API_ID}")
print(f"API_HASH = {'✅ есть' if API_HASH else '❌ нет'}")
print(f"BOT_TOKEN = {'✅ есть' if BOT_TOKEN else '❌ нет'}")
print(f"CHAT_ID = {CHAT_ID}")
print(f"CHECK_INTERVAL_HOURS = {CHECK_INTERVAL_HOURS}\n")

missing = [k for k, v in {
    "API_ID": API_ID, "API_HASH": API_HASH, "BOT_TOKEN": BOT_TOKEN, "CHAT_ID": CHAT_ID
}.items() if not v]

if missing:
    print(f"❌ Ошибка: отсутствуют ключи {', '.join(missing)}")
    sys.exit(1)
else:
    print("✅ Все ключи найдены. Стартуем...\n")

# =============================
# Список чатов/каналов для мониторинга
# =============================
CHAT_IDS = [
    -1001356532108,
    -1002363500314,
    -1001311121622,
    -1001388027785,
    -1001508876175,
    -1001277376699,
    -1001946343717,
    -1001341855810,
    -1001278212382,
    -1001361144761,
    -1001706773923,
    -1001643118953,
    -1001032422089,
    -1001716678830,
    -1001540608753,
    -1001867725040,
    -1001726137174,
    -1002624129997,
    -1002490371800   # 🔸 добавлен новый чат
]

# =============================
# Ключевые слова
# =============================
KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфингу","сёрфинг","серфингом","сёрфингом",
    "сёрф","серф","инструктор по серфингу","серфурок","уроки серфинга","уроки сёрфинга",
    "сёрфтренер","сёрфкемп","занятия по сёрфингу","тренера по серфингу","тренер по серфингу",
    "серфтренер","занятие по серфингу","серфкемп","ищу инструктора по серфингу","серфуроки",
    "инструктор","инструкторсерф","surf","surfing","инструкторсерфинга"
]

def contains_keyword(text):
    if not text:
        return False
    lc = text.lower()
    return any(kw in lc for kw in KEYWORDS)

# =============================
# Инициализация клиента
# =============================
client = TelegramClient("surf_session", int(API_ID), API_HASH)

# =============================
# Безопасная отправка сообщений
# =============================
async def send_message_safe(to_chat, text):
    try:
        await client.send_message(int(to_chat), text)
        print(f"[{local_time()}] 📩 Отправлено: {text[:120]!s}")
    except FloodWaitError as e:
        wait = e.seconds + 5
        print(f"[{local_time()}] ⏳ FloodWait {e.seconds} сек, ждём...")
        await asyncio.sleep(wait)
        await client.send_message(int(to_chat), text)
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка отправки: {e}")

# =============================
# Форматирование найденных сообщений
# =============================
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
    try:
        channel_username = (await client.get_entity(channel)).username
        link = f"https://t.me/{channel_username}/{msg.id}" if channel_username else ""
    except Exception:
        link = ""

    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {local_datetime()}\n\n{text_snippet}\n🔗 {link}"

# =============================
# Проверка истории при запуске
# =============================
async def check_history_and_send():
    print(f"[{local_time()}] 🔎 Проверка истории в {len(CHAT_IDS)} чатах...")
    found = []
    for ch in CHAT_IDS:
        try:
            entity = await client.get_entity(ch)
            msgs = await client.get_messages(entity, limit=50)
            for m in msgs:
                if m.message and contains_keyword(m.message):
                    formatted = await format_message(ch, m)
                    found.append(formatted)
            await asyncio.sleep(1.2)
        except FloodWaitError as e:
            wait = e.seconds + 5
            print(f"[{local_time()}] ⏳ FloodWait {e.seconds} сек при чтении {ch}, ждём...")
            await asyncio.sleep(wait)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка при чтении {ch}: {e}")

    if found:
        batch = "\n\n---\n\n".join(found)
        MAX_LEN = 4000
        parts = [batch[i:i+MAX_LEN] for i in range(0, len(batch), MAX_LEN)]
        for p in parts:
            await send_message_safe(CHAT_ID, f"🌊 Найдено совпадений ({len(found)}):\n\n{p}")
        print(f"[{local_time()}] ✅ Отправлено {len(found)} найденных сообщений.")
    else:
        print(f"[{local_time()}] 😴 Совпадений не найдено.")

# =============================
# Реальное время — обработчик новых сообщений
# =============================
@client.on(events.NewMessage(chats=CHAT_IDS))
async def new_message_handler(event):
    try:
        text = event.message.message or ""
        print(f"[{local_time()}] 🆕 Новое сообщение: {text[:100]!s}")
        if contains_keyword(text):
            channel_name = getattr(event.chat, "username", None) or getattr(event.chat, "title", str(event.chat))
            formatted = await format_message(channel_name, event.message)
            await send_message_safe(CHAT_ID, formatted)
            print(f"[{local_time()}] ✅ Совпадение найдено и отправлено.")
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка в обработчике: {e}")

# =============================
# Периодический пинг
# =============================
async def periodic_ping():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        await send_message_safe(CHAT_ID, f"🏄‍♂️ SurfHunter онлайн — {local_time()}")
        print(f"[{local_time()}] ⏱️ Пинг отправлен.")

# =============================
# Основной старт
# =============================
async def main():
    try:
        print(f"[{local_time()}] 🚀 Запуск клиента...")
        await client.start(bot_token=BOT_TOKEN)
        me = await client.get_me()
        print(f"[{local_time()}] ✅ Бот @{me.username or me.first_name} запущен!")

        await send_message_safe(CHAT_ID, f"🌊 Все ключи найдены, бот готов!\n🤙 Волны чекаем, всё стабильно.\n🕒 Время запуска: {local_time()}")

        await check_history_and_send()
        asyncio.create_task(periodic_ping())

        await client.run_until_disconnected()

    except FloodWaitError as e:
        wait = e.seconds + 5
        print(f"[{local_time()}] ⏳ FloodWait {e.seconds} сек. Ждём {wait} сек...")
        await asyncio.sleep(wait)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"[{local_time()}] 💥 Критическая ошибка: {e}")
        await asyncio.sleep(60)
        os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"[{local_time()}] 🛑 Остановка вручную.")