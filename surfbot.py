import os
import asyncio
import random
from telethon import TelegramClient, errors
from datetime import datetime

# =============================
# Конфигурация
# =============================
API_ID = int(os.environ.get("API_ID"))         # твой API_ID
API_HASH = os.environ.get("API_HASH")          # твой API_HASH
OWNER_ID = int(os.environ.get("OWNER_ID"))     # твой Telegram ID
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", 0.75))  # 45 минут

# Создаем клиент для живого аккаунта
client = TelegramClient("user_session", API_ID, API_HASH)

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

# =============================
# Вспомогательные функции
# =============================
def contains_keyword(text):
    text = text.lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def format_message(channel, msg):
    # Автор
    author = "—"
    try:
        sender = asyncio.run(msg.get_sender())
        if sender:
            author = (sender.first_name or "") + " " + (sender.last_name or "")
            if getattr(sender, "username", None):
                author += f" (@{sender.username})"
    except Exception:
        pass
    text_snippet = (msg.message[:700] + "...") if len(msg.message or "") > 700 else (msg.message or "")
    link = f"https://t.me/{getattr(msg.to_id, 'channel_id', msg.id)}" if not getattr(msg, 'id', None) else f"https://t.me/{channel}/{msg.id}"
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {msg.date.strftime('%d.%m %H:%M')}\n\n{text_snippet}\n🔗 {link}"

# =============================
# Основной цикл
# =============================
async def main():
    await client.start()  # Попросит код при первом запуске
    me = await client.get_me()
    print(f"🚀 SurfFinder запущен. Аккаунт: {me.username or me.first_name}")

    while True:
        start_time = datetime.utcnow()
        found_messages = []

        for channel in CHANNELS:
            try:
                entity = await client.get_entity(channel)
                messages = await client.get_messages(entity, limit=50)
                for msg in messages:
                    if msg.message and contains_keyword(msg.message):
                        formatted = format_message(channel, msg)
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
                await client.send_message('me', batch_message)  # уведомление в Saved Messages
                print(f"✅ Отправлено {len(found_messages)} сообщений.")
            except Exception as e:
                print(f"❌ Ошибка отправки сообщений: {e}")

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        print(f"🕒 Цикл завершен. Найдено {len(found_messages)} сообщений. Время: {elapsed:.1f}s. Следующая проверка через {CHECK_INTERVAL_HOURS*60:.0f} минут.")
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

# =============================
# Старт
# =============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")