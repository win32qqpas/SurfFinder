import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, errors, events

# =============================
# Настройка бота
# =============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# Создаём клиент бота
client = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# =============================
# Списки каналов и ключевых слов
# =============================
CHANNELS = [
    "balichatik","voprosBali","bali_russia_choogl","cangguchat",
    "bali_ubud_changu","balichat_canggu","balichat_bukit","balichatnash",
    "balichat_bukitwoman","balichatfit","balichatsurfing","balisurfer",
    "ChatCanggu","bukit_bali2","baliaab666","bali_chat","bali_ua"
]

KEYWORDS = [
    "серфинг","серф","инструктор по серфингу","серфурок",
    "уроки серфинга","тренер по серфингу","серфтренер",
    "занятие по серфингу","серфкемп","ищу инструктора по серфингу"
]

CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 0.333333))  # 20 минут

# =============================
# Основной цикл
# =============================
async def main():
    await client.start()
    print("🚀 SurfFinder запущен!")

    while True:
        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                messages = await client.get_messages(entity, limit=50)
                for msg in messages:
                    text = msg.message
                    if text and any(keyword.lower() in text.lower() for keyword in KEYWORDS):
                        link = f"https://t.me/{channel}/{msg.id}" if hasattr(msg, "id") else f"https://t.me/{channel}"
                        await client.send_message(OWNER_ID, f"Найдено сообщение:\n\n{text}\n\nСсылка: {link}")
            except errors.FloodWaitError as e:
                print(f"⏳ FloodWait {e.seconds} сек. для {channel}")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"Ошибка при поиске в {channel}: {e}")

        print(f"🤙 Проверка завершена. Следующая через {CHECK_INTERVAL_HOURS*60:.0f} минут.")
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

# =============================
# Запуск
# =============================
if __name__ == "__main__":
    asyncio.run(main())