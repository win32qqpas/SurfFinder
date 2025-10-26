import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# === 🔍 Проверяем переменные окружения ===
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", 1.0))

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
    raise SystemExit(1)
else:
    print("✅ Все ключи найдены. Стартуем...\n")

# === ⚙️ Инициализация клиента ===
client = TelegramClient("surf_session", int(API_ID), API_HASH)

# === 📩 Обработка сообщений из группы ===
@client.on(events.NewMessage(chats=int(CHAT_ID)))
async def handler(event):
    try:
        messages = await client.get_messages(int(CHAT_ID), limit=50)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔹 Получено {len(messages)} сообщений.")
    except Exception as e:
        print(f"⚠️ Ошибка при чтении сообщений: {e}")

# === 🕒 Проверка активности ===
async def hourly_check():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        try:
            now = datetime.now().strftime('%H:%M')
            await client.send_message(int(CHAT_ID), f"🏄‍♂️ SurfHunter онлайн ({now})")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️ Проверка активности отправлена.")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке сообщения: {e}")

# === 🚀 Основной цикл с FloodWait и уведомлением в ЛС ===
async def main():
    try:
        await client.start(bot_token=BOT_TOKEN)
        me = await client.get_me()
        print(f"🚀 Бот @{me.username or me.first_name} запущен ({datetime.now().strftime('%d.%m %H:%M')})")

        # 💬 Сообщение в личку при старте
        try:
            await client.send_message(int(CHAT_ID),
                f"🌊 Все ключи найдены, бот готов!\n"
                f"🤙 Волны чекаем, всё стабильно.\n"
                f"🕒 Время запуска: {datetime.now().strftime('%H:%M')}")
            print("📩 Сообщение о готовности отправлено.")
        except Exception as e:
            print(f"⚠️ Не удалось отправить сообщение о готовности: {e}")

        # Фоновая проверка активности
        asyncio.create_task(hourly_check())

        await client.run_until_disconnected()

    except FloodWaitError as e:
        wait = e.seconds + 5
        print(f"⏳ FloodWait: Telegram просит подождать {e.seconds} секунд. Ждём {wait} сек...")
        await asyncio.sleep(wait)
        print("🔁 Повторное подключение после FloodWait...\n")
        await main()

    except Exception as e:
        print(f"💥 Ошибка: {e}")
        await asyncio.sleep(60)
        print("🔁 Перезапуск после ошибки...\n")
        await main()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановка вручную.")