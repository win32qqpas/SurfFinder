import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, errors

# === Получаем переменные окружения ===
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "1"))

# === Проверяем ключи ===
print("🔍 Проверка переменных окружения...")
if not all([API_ID, API_HASH, BOT_TOKEN, CHAT_ID]):
    print("❌ Ошибка: не найдены все ключи (API_ID, API_HASH, BOT_TOKEN, CHAT_ID)")
    raise SystemExit("⛔️ Завершено: отсутствуют необходимые ключи.")
print("✅ Все ключи найдены. Стартуем...\n")

# === Инициализация клиента ===
client = TelegramClient("surfbot_session", int(API_ID), API_HASH)

async def notify_startup():
    """Отправка уведомления о запуске"""
    try:
        await client.send_message(int(CHAT_ID),
            f"🚀 SurfBot запущен и активен!\n⏰ {datetime.now().strftime('%d.%m %H:%M')}")
        print("📨 Уведомление о запуске отправлено.")
    except errors.FloodWaitError as e:
        print(f"⏳ FloodWait: подождем {e.seconds} секунд...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"⚠️ Ошибка при отправке уведомления: {e}")

async def periodic_check():
    """Проверка статуса каждые CHECK_INTERVAL_HOURS часов"""
    interval = CHECK_INTERVAL_HOURS * 3600
    while True:
        try:
            await client.send_message(int(CHAT_ID),
                f"🤙 SurfBot всё ещё активен!\nВремя: {datetime.now().strftime('%d.%m %H:%M')}")
            print(f"✅ Сообщение о проверке отправлено ({datetime.now().strftime('%H:%M')})")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке проверки: {e}")
        await asyncio.sleep(interval)

@client.on(events.NewMessage)
async def handle_message(event):
    """Обработка входящих сообщений"""
    text = event.message.message.lower()
    if "ping" in text:
        await event.respond("🏄‍♂️ pong! Я на волне 🌊")

async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"🤖 Бот {me.username} запущен в {datetime.now().strftime('%d.%m %H:%M')}")

    await notify_startup()
    asyncio.create_task(periodic_check())
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 SurfBot остановлен вручную.")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")