import os
import asyncio
import random
from datetime import datetime, timezone
from telethon import TelegramClient, events, errors

# =============================
# 🔧 Переменные окружения
# =============================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = int(os.environ.get("CHAT_ID", "2084700847"))
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 1.0))

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise SystemExit("❌ ERROR: Не заданы API_ID / API_HASH / BOT_TOKEN")

print("✅ Все ключи найдены. Стартуем...")

# =============================
# 📡 Каналы и ключевые слова
# =============================
CHANNELS = [
    "balichatik", "voprosBali", "bali_russia_choogl", "cangguchat",
    "bali_ubud_changu", "balichat_canggu", "balichat_bukit", "balichatnash",
    "balichat_bukitwoman", "balichatfit", "balichatsurfing", "balisurfer",
    "ChatCanggu", "bukit_bali2", "baliaab666", "bali_chat", "bali_ua"
]

KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфингу","сёрфинг","серфингом","сёрфингом","сёрф","серф",
    "инструктор по серфингу","уроки серфинга","уроки сёрфинга","сёрфтренер","сёрфкемп",
    "занятия по сёрфингу","тренера по серфингу","тренер по серфингу","серфтренер","занятие по серфингу",
    "серфкемп","ищу инструктора по серфингу"
]

# =============================
# 🚀 Инициализация клиента
# =============================
client = TelegramClient("bot_session", API_ID, API_HASH)

def contains_keyword(text):
    return any(kw.lower() in text.lower() for kw in KEYWORDS)

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

    text_snippet = (msg.message[:700] + "...") if msg.message and len(msg.message) > 700 else (msg.message or "")
    link = f"https://t.me/{channel}/{msg.id}" if getattr(msg, "id", None) else f"https://t.me/{channel}"
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {msg.date.strftime('%d.%m %H:%M')}\n\n{text_snippet}\n🔗 {link}"

# =============================
# 🧠 Проверка истории каналов
# =============================
async def check_history():
    found_messages = []
    for channel in CHANNELS:
        try:
            entity = await client.get_entity(channel)
            async for msg in client.iter_messages(entity, limit=100):
                if msg.message and contains_keyword(msg.message):
                    formatted = await format_message(channel, msg)
                    found_messages.append(formatted)
            await asyncio.sleep(1 + random.random() * 2)
        except errors.FloodWaitError as e:
            print(f"⏳ FloodWait: {e.seconds} сек для {channel}")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"❌ Ошибка при обработке {channel}: {e}")
            await asyncio.sleep(2)

    if found_messages:
        batch = "\n\n---\n\n".join(found_messages)
        try:
            await client.send_message(CHAT_ID, f"🌊 Найдено {len(found_messages)} сообщений:\n\n{batch}")
            print(f"✅ Отправлено {len(found_messages)} сообщений.")
        except Exception as e:
            print(f"❌ Ошибка отправки сообщений: {e}")

# =============================
# ⏰ Основной процесс
# =============================
async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"🚀 Бот @{me.username} запущен и работает!")

    try:
        await client.send_message(CHAT_ID, f"🚀 Бот @{me.username} запущен {datetime.now().strftime('%d.%m %H:%M')}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить приветственное сообщение: {e}")

    # Слушаем новые сообщения
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        text = event.message.message or ""
        if contains_keyword(text):
            formatted = await format_message(event.chat.username or event.chat.title, event.message)
            try:
                await client.send_message(CHAT_ID, formatted)
                print(f"✅ Новое сообщение из {event.chat.title}")
            except Exception as e:
                print(f"❌ Ошибка отправки нового сообщения: {e}")

    # Периодический цикл проверок
    while True:
        await check_history()
        print(f"🕒 Проверка завершена. Следующая через {CHECK_INTERVAL_HOURS * 60:.0f} минут.")
        try:
            await client.send_message(CHAT_ID, f"✅ Цикл проверки завершен {datetime.now().strftime('%H:%M')}")
        except Exception:
            pass
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

# =============================
# ▶️ Запуск
# =============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлено пользователем")