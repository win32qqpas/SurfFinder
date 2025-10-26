import os
import asyncio
import random
from telethon import TelegramClient, events, errors
from datetime import datetime

# =============================
# Переменные окружения
# =============================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 0.75))

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("❌ API_ID, API_HASH или BOT_TOKEN не заданы!")

# =============================
# Каналы и ключевые слова
# =============================
CHANNELS = ["balichatik", "voprosBali", "bali_russia_choogl"]  # и так далее
KEYWORDS = ["серфинг", "серфингу", "уроки серфинга"]  # пример

# =============================
# Инициализация клиента
# =============================
client = TelegramClient('bot_session', API_ID, API_HASH)

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
    link = f"https://t.me/{channel}/{msg.id}" if getattr(msg, "id", None) else ""
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {msg.date.strftime('%d.%m %H:%M')}\n\n{text_snippet}\n🔗 {link}"

async def check_history():
    found_messages = []
    for channel in CHANNELS:
        try:
            entity = await client.get_entity(channel)
            messages = await client.get_messages(entity, limit=100)
            for msg in messages:
                if msg.message and contains_keyword(msg.message):
                    formatted = await format_message(channel, msg)
                    found_messages.append(formatted)
            await asyncio.sleep(1 + random.random()*2)
        except errors.FloodWaitError as e:
            print(f"⏳ FloodWait {e.seconds}s для {channel}, жду...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"❌ Ошибка при обработке {channel}: {e}")
            await asyncio.sleep(2)
    if found_messages:
        batch_message = "\n\n---\n\n".join(found_messages)
        try:
            await client.send_message('me', batch_message)
            print(f"✅ Отправлено {len(found_messages)} сообщений из истории.")
        except Exception as e:
            print(f"❌ Ошибка отправки сообщений: {e}")

# =============================
# Основной цикл
# =============================
async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    
    # Уведомление о старте
    await client.send_message('me', f"🚀 {me.username or me.first_name} успешно запущен! {datetime.now().strftime('%d.%m %H:%M')}")
    print(f"🚀 {me.username or me.first_name} запущен!")

    # Проверяем историю сразу
    await check_history()

    # Обработчик новых сообщений
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        try:
            text = event.message.message
            if contains_keyword(text):
                formatted = await format_message(event.chat.username or event.chat.title, event.message)
                await client.send_message('me', formatted)
                print(f"✅ Новое сообщение из {event.chat.title}")
        except errors.FloodWaitError as e:
            print(f"⏳ FloodWait {e.seconds}s при новом сообщении, жду...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"❌ Ошибка при обработке нового сообщения: {e}")

    # Периодический цикл
    while True:
        print(f"🕒 Цикл проверки завершен. Следующая проверка через {CHECK_INTERVAL_HOURS*60:.0f} минут.")
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        await check_history()

        # Ежечасное уведомление о работе бота
        await client.send_message('me', f"⏰ {me.username or me.first_name} всё ещё работает. Время: {datetime.now().strftime('%d.%m %H:%M')}")

# =============================
# Старт
# =============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Остановлено пользователем")