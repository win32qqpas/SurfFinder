import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events

# === Настройки из Render Environment ===
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Проверка ключей ===
missing_keys = [k for k, v in {
    "API_ID": API_ID, "API_HASH": API_HASH, "BOT_TOKEN": BOT_TOKEN, "CHAT_ID": CHAT_ID
}.items() if not v]

if missing_keys:
    print(f"❌ Ошибка: отсутствуют ключи {', '.join(missing_keys)}")
else:
    print("✅ Все ключи найдены. Стартуем...")

# === Инициализация клиента ===
client = TelegramClient('surf_session', int(API_ID), API_HASH)

# === Обработка сообщений ===
@client.on(events.NewMessage(chats=int(CHAT_ID)))
async def handler(event):
    try:
        messages = await client.get_messages(int(CHAT_ID), limit=50)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔹 Получено {len(messages)} сообщений.")
    except Exception as e:
        print(f"⚠️ Ошибка при чтении сообщений: {e}")

# === Проверка активности ===
async def hourly_check():
    while True:
        await asyncio.sleep(3600)  # каждый час
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ Проверка — бот активен.")
        try:
            await client.send_message(int(CHAT_ID), f"🏄‍♂️ SurfHunter онлайн {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке сообщения: {e}")

# === Основной запуск ===
async def main():
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    print(f"🚀 Бот {me.username or me.first_name} запущен в {datetime.now().strftime('%d.%m %H:%M')}")

    try:
        await client.send_message(int(CHAT_ID), f"🤙 SurfHunter запущен и готов к ловле волн! 🌊 {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение в Telegram: {e}")

    asyncio.create_task(hourly_check())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())