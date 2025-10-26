import os
import sys
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# =============================
# Настройки часового пояса
# =============================
# Локальное время: GMT+8 (Бали)
TZ_OFFSET = 8  # часы

def local_time():
    """Возвращает текущее местное время (GMT+TZ_OFFSET) в формате HH:MM."""
    return (datetime.utcnow() + timedelta(hours=TZ_OFFSET)).strftime('%H:%M')

def local_datetime():
    """Возвращает текущее местное дату+время (GMT+TZ_OFFSET) в формате DD.MM HH:MM."""
    return (datetime.utcnow() + timedelta(hours=TZ_OFFSET)).strftime('%d.%m %H:%M')

# =============================
# Читаем переменные окружения
# =============================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "1").strip())

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
    sys.exit(1)
else:
    print("✅ Все ключи найдены. Стартуем...\n")

# =============================
# Инициализация Telethon клиента
# =============================
client = TelegramClient("surf_session", int(API_ID), API_HASH)

# =============================
# Вспомогательная безопасная отправка (с обработкой FloodWait)
# =============================
async def send_message_safe(chat_id, text):
    """Отправляет сообщение и при FloodWait ждёт нужное время, затем повторяет."""
    try:
        await client.send_message(int(chat_id), text)
        print(f"[{local_time()}] 📩 Отправлено: {text[:120]!s}")
    except FloodWaitError as e:
        wait = e.seconds + 5
        print(f"[{local_time()}] ⏳ FloodWait: ждём {e.seconds} сек (плюс буфер) = {wait} сек...")
        await asyncio.sleep(wait)
        try:
            await client.send_message(int(chat_id), text)
            print(f"[{local_time()}] 📩 Повторная отправка после FloodWait успешна.")
        except Exception as e2:
            print(f"[{local_time()}] ⚠️ Ошибка при повторной отправке: {e2}")
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка при отправке сообщения: {e}")

# =============================
# Список каналов (как у тебя)
# =============================
CHANNELS = [
    "balichatik","voprosBali","bali_russia_choogl","cangguchat",
    "bali_ubud_changu","balichat_canggu","balichat_bukit","balichatnash",
    "balichat_bukitwoman","balichatfit","balichatsurfing","balisurfer",
    "ChatCanggu","bukit_bali2","baliaab666","bali_chat","bali_ua"
]

KEYWORDS = [
    "серфинг","серфинга","серфингу","сёрфинг","сёрф","серф",
    "инструктор по серфингу","уроки серфинга","серфтренер",
    "занятия по серфинг", "занятия по серфингу", "тренер по серфингу",
    "серфкемп","сёрфкемп","ищу инструктора по серфингу"
]

def contains_keyword(text):
    if not text:
        return False
    text = text.lower()
    return any(kw in text for kw in KEYWORDS)

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
    return f"📍 {channel}\n👤 {author.strip()}\n🕒 {local_datetime()}\n\n{text_snippet}\n🔗 {link}"

# =============================
# Проверяем историю каналов (последние 50 сообщений)
# =============================
async def check_history_and_send():
    print(f"[{local_time()}] 🔎 Начинаем проверку истории каналов...")
    found = []
    for ch in CHANNELS:
        try:
            entity = await client.get_entity(ch)
            msgs = await client.get_messages(entity, limit=50)
            for m in msgs:
                if m.message and contains_keyword(m.message):
                    formatted = await format_message(ch, m)
                    found.append(formatted)
            await asyncio.sleep(1 + (0.5 * (os.urandom(1)[0] % 3)))  # небольшой рандомизированный sleep
        except FloodWaitError as e:
            wait = e.seconds + 5
            print(f"[{local_time()}] ⏳ FloodWait при чтении {ch}: ждём {wait} сек...")
            await asyncio.sleep(wait)
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка чтения канала {ch}: {e}")

    if found:
        batch = "\n\n---\n\n".join(found)
        # Разбиваем на несколько сообщений если слишком длинное
        MAX_LEN = 4000
        pieces = [batch[i:i+MAX_LEN] for i in range(0, len(batch), MAX_LEN)]
        for p in pieces:
            await send_message_safe(CHAT_ID, f"🌊 Найдено совпадений:\n\n{p}")
        print(f"[{local_time()}] ✅ Отправлено {len(found)} найденных сообщений.")
    else:
        print(f"[{local_time()}] 😴 Совпадений в истории не найдено.")

# =============================
# Слушаем новые сообщения (в режиме реального времени)
# =============================
@client.on(events.NewMessage(chats=CHANNELS))
async def new_message_handler(event):
    try:
        text = event.message.message
        if contains_keyword(text):
            channel_username = getattr(event.chat, "username", None) or getattr(event.chat, "title", str(event.chat))
            formatted = await format_message(channel_username, event.message)
            await send_message_safe(CHAT_ID, formatted)
            print(f"[{local_time()}] ✅ Новое совпадение из {channel_username} отправлено.")
    except Exception as e:
        print(f"[{local_time()}] ⚠️ Ошибка в обработчике новых сообщений: {e}")

# =============================
# Периодический пинг (каждые CHECK_INTERVAL_HOURS часов)
# =============================
async def periodic_ping():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
        try:
            await send_message_safe(CHAT_ID, f"🏄‍♂️ SurfHunter онлайн — {local_time()}")
            print(f"[{local_time()}] ⏱️ Пинг отправлен.")
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Ошибка при пинге: {e}")

# =============================
# Основной цикл с надежной обработкой FloodWait и ошибок
# =============================
async def main():
    try:
        print(f"[{local_time()}] 🚀 Старт Telethon клиента...")
        await client.start(bot_token=BOT_TOKEN)
        await asyncio.sleep(1.5)  # небольшой запас времени на инициализацию
        me = await client.get_me()
        print(f"[{local_time()}] ✅ Бот @{me.username or me.first_name} запущен (локальное время).")

        # Отправляем приветственное личное сообщение
        try:
            await send_message_safe(CHAT_ID,
                f"🌊 Все ключи найдены, бот готов!\n"
                f"🤙 Волны чекаем, всё стабильно.\n"
                f"🕒 Время запуска: {local_time()}"
            )
            print(f"[{local_time()}] 📩 Уведомление о готовности отправлено в личку.")
        except Exception as e:
            print(f"[{local_time()}] ⚠️ Не удалось отправить уведомление о готовности: {e}")

        # Проверяем историю один раз при старте
        await check_history_and_send()

        # Запускаем параллельно: слушатель новых сообщений (он уже зарегистрирован) и периодический пинг
        asyncio.create_task(periodic_ping())

        # Держим клиент подключённым
        await client.run_until_disconnected()

    except FloodWaitError as e:
        wait = e.seconds + 5
        print(f"[{local_time()}] ⏳ FloodWait: Telegram просит подождать {e.seconds} сек. Ждём {wait} сек...")
        await asyncio.sleep(wait)
        print(f"[{local_time()}] 🔁 Попробуем запустить снова после FloodWait.")
        # безопасный перезапуск процесса
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        print(f"[{local_time()}] 💥 Критическая ошибка: {e}")
        await asyncio.sleep(60)
        print(f"[{local_time()}] 🔁 Перезапуск после ошибки.")
        os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"[{local_time()}] 🛑 Остановка вручную.")