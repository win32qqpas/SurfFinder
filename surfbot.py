import os
import asyncio
import random
from telethon import TelegramClient, events, errors
from datetime import datetime

# =============================
# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# =============================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # Твой ID, чтобы бот присылал тебе результаты
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 1))

print("🔍 Проверяем переменные окружения:")
print(f"API_ID = {API_ID}")
print(f"API_HASH = {'✅ есть' if API_HASH else '❌ нет'}")
print(f"BOT_TOKEN = {'✅ есть' if BOT_TOKEN else '❌ нет'}")
print(f"CHAT_ID = {CHAT_ID}")
print(f"CHECK_INTERVAL_HOURS = {CHECK_INTERVAL_HOURS}")

if not all([API_ID, API_HASH, BOT_TOKEN, CHAT_ID]):
    raise SystemExit("❌ Ошибка: Не найдены все ключи. Проверь Environment Variables в Render.")

print("✅ Все ключи найдены. Стартуем...")

# =============================
# СПИСОК КАНАЛОВ ДЛЯ МОНИТОРИНГА
# =============================
CHANNELS = [
    "balichatik","voprosBali","bali_russia_choogl","cangguchat",
    "bali_ubud_changu","balichat_canggu","balichat_bukit","balichatnash",
    "balichat_bukitwoman","balichatfit","balichatsurfing","balisurfer",
    "ChatCanggu","bukit_bali2","baliaab666","bali_chat","bali_ua"
]

# =============================
# КЛЮЧЕВЫЕ СЛОВА
# =============================
KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфинг","сёрф","серф",
    "инструктор по серфингу","уроки серфинга","серфтренер",
    "занятия по серфингу","тренер по серфингу","серфкемп","сёрфкемп"
]

# =============================
# ИНИЦИАЛИЗАЦИЯ КЛИЕНТА
# =============================
client = TelegramClient("surfbot_session", int(API_ID), API_HASH)

# =============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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

# =============================
# ПРОВЕРКА ИСТОРИИ КАНАЛОВ
# =============================
async def check_history():
    print("🔎 Проверяем историю сообщений...")
    found_messages = []
    for channel in CHANNELS:
        try:
            entity = await client.get_entity(channel)
            messages = await client.get_messages(entity, limit=50)
            for msg in messages:
                if msg.message and contains_keyword(msg.message):
                    formatted = await format_message(channel, msg)
                    found_messages.append(formatted)
            await asyncio.sleep(1 + random.random() * 2)
        except errors.FloodWaitError as e:
            print(f"⏳ FloodWait: ждём {e.seconds} секунд для {channel}")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"❌ Ошибка при обработке {channel}: {e}")
            await asyncio.sleep(2)

    if found_messages:
        batch_message = "\n\n---\n\n".join(found_messages)
        try:
            await client.send_message(int(CHAT_ID), f"🌊 Найдено {len(found_messages)} сообщений:\n\n{batch_message}")
            print(f"✅ Отправлено {len(found_messages)} сообщений.")
        except Exception as e:
            print(f"❌ Ошибка при отправке: {e}")
    else:
        print("😴 Ничего нового не найдено.")

# =============================
# ОСНОВНОЙ ЦИКЛ
# =============================
async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"🚀 Бот @{me.username} успешно запущен!")

    # Сообщаем в Telegram
    try:
        await client.send_message(int(CHAT_ID), f"🚀 @{me.username} запущен! ({datetime.now().strftime('%d.%m %H:%M')})")
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение о запуске: {e}")

    # Проверка истории при запуске
    await check_history()

    # Подписка на новые сообщения
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        text = event.message.message
        if contains_keyword(text):
            formatted = await format_message(event.chat.username or event.chat.title, event.message)
            try:
                await client.send_message(int(CHAT_ID), formatted)
                print(f"✅ Новое сообщение из {event.chat.title}")
            except Exception as e:
                print(f"❌ Ошибка при отправке нового сообщения: {e}")

    # Периодический перезапуск
    while True:
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        print(f"🔁 Проверка каждые {CHECK_INTERVAL_HOURS} часов ({datetime.now().strftime('%H:%M')})")
        await check_history()

# =============================
# СТАРТ ПРОГРАММЫ
# =============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлено вручную")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")