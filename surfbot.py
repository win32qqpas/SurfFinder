import os
import asyncio
import random
from telethon import TelegramClient, events, errors
from datetime import datetime, timezone

# =============================
# Проверка и загрузка переменных окружения
# =============================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 0.75))
CHAT_ID = os.environ.get("CHAT_ID")  # Можно использовать для отправки сообщений напрямую

if not API_ID or not API_HASH:
    raise SystemExit("ERROR: API_ID или API_HASH не заданы. Добавь их в Environment Variables.")
if not BOT_TOKEN:
    raise SystemExit("ERROR: BOT_TOKEN не задан. Создай бота через BotFather и добавь токен в Environment Variables.")

API_ID = int(API_ID)  # Обязательно конвертируем в число

print("✅ API_ID, API_HASH и BOT_TOKEN найдены.")

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
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

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
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {msg.date.strftime('%d.%m %H:%M')}\n\n{text_snippet}\n🔗 {link}"

# =============================
# Проверка истории каналов
# =============================
async def check_history():
    found_messages = []
    for channel in CHANNELS:
        try:
            entity = await client.get_entity(channel)
            messages = await client.get_messages(entity, limit=100)  # теперь 100 сообщений
            for msg in messages:
                if msg.message and contains_keyword(msg.message):
                    formatted = await format_message(channel, msg)
                    found_messages.append(formatted)
            await asyncio.sleep(1 + random.random()*2)
        except errors.FloodWaitError as e:
            print(f"⏳ FloodWait {e.seconds}s для {channel}, спим...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"❌ Ошибка при обработке {channel}: {e}")
            await asyncio.sleep(2)

    if found_messages:
        batch_message = "\n\n---\n\n".join(found_messages)
        try:
            if CHAT_ID:
                await client.send_message(int(CHAT_ID), batch_message)
            else:
                await client.send_message('me', batch_message)
            print(f"✅ История: отправлено {len(found_messages)} сообщений.")
        except Exception as e:
            print(f"❌ Ошибка отправки сообщений из истории: {e}")

# =============================
# Основной цикл
# =============================
async def main():
    await client.start()
    me = await client.get_me()
    print(f"🚀 SurfFinder Bot запущен. Имя бота: {me.username or me.first_name}")

    # Проверяем историю сразу
    await check_history()

    # Слушаем новые сообщения
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        text = event.message.message
        if contains_keyword(text):
            formatted = await format_message(event.chat.username or event.chat.title, event.message)
            try:
                if CHAT_ID:
                    await client.send_message(int(CHAT_ID), formatted)
                else:
                    await client.send_message('me', formatted)
                print(f"✅ Новое сообщение из {event.chat.title}")
            except Exception as e:
                print(f"❌ Ошибка отправки нового сообщения: {e}")

    # Периодический цикл
    while True:
        print(f"🕒 Цикл проверки завершен. Следующая проверка через {CHECK_INTERVAL_HOURS*60:.0f} минут.")
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

# =============================
# Старт
# =============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")