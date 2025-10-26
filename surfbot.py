import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events

# === Получаем переменные окружения (Render Environment Variables) ===
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Проверка обязательных ключей ===
missing_keys = [k for k, v in {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "CHAT_ID": CHAT_ID
}.items() if not v]

if missing_keys:
    print(f"❌ Ошибка: отсутствуют ключи {', '.join(missing_keys)}")
    raise SystemExit()
else:
    print("✅ Все ключи найдены. Стартуем...")

# === Инициализация клиента ===
client = TelegramClient('surf_session', int(API_ID), API_HASH)


# === Обработка новых сообщений ===
@client.on(events.NewMessage(chats=int(CHAT_ID)))
async def message_handler(event):
    try:
        messages = await client.get_messages(int(CHAT_ID), limit=50)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔹 Обновлено {len(messages)} сообщений.")
    except Exception as e:
        print(f"⚠️ Ошибка при чтении сообщений: {e}")


# === Проверка активности каждый час ===
async def hourly_check():
    while True:
        await asyncio.sleep(3600)  # Проверка каждые 60 минут
        time_now = datetime.now().strftime('%H:%M')
        print(f"[{time_now}] ⏱️ Проверка — бот активен.")
        try:
            await client.send_message(int(CHAT_ID), f"🏄‍♂️ SurfHunter на связи {time_now}")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке сообщения: {e}")


# === Основная функция ===
async def main():
    try:
        await client.start(bot_token=BOT_TOKEN)
        me = await client.get_me()
        print(f"🚀 Бот @{me.username} успешно запущен ({datetime.now().strftime('%d.%m %H:%M')})")

        # Отправляем приветственное сообщение в канал/группу
        await client.send_message(int(CHAT_ID), f"🤙 SurfHunter запущен 🌊 {datetime.now().strftime('%H:%M')}")

        # Запускаем проверку активности
        asyncio.create_task(hourly_check())

        # Держим соединение
        await client.run_until_disconnected()

    except Exception as e:
        print(f"💥 Ошибка запуска: {e}")
        await asyncio.sleep(60)  # Подождать минуту и попробовать снова
        await main()


if __name__ == "__main__":
    asyncio.run(main())