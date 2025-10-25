# SurfFinder — Telegram бот для поиска клиентов по ключевым словам
# Работает каждые 20 минут, ищет по публичным чатам и присылает тебе результаты
# Автор: ты и твоя волна 🌊

import os
import asyncio
import re
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, errors

# ==== Конфигурация ====
API_ID = int(os.environ.get('API_ID', '0'))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
OWNER_ID = int(os.environ.get('OWNER_ID', '0'))

# Проверять каждые 20 минут (0.333333 часа)
CHECK_INTERVAL_HOURS = float(os.environ.get('CHECK_INTERVAL_HOURS', '0.333333'))

CHANNELS_RAW = os.environ.get('CHANNELS', '')
KEYWORDS_RAW = os.environ.get('KEYWORDS', '')

CHANNELS = [c.strip() for c in CHANNELS_RAW.split(',') if c.strip()]
KEYWORDS = [k.strip().lower() for k in KEYWORDS_RAW.split(',') if k.strip()]

if not (API_ID and API_HASH and BOT_TOKEN and OWNER_ID and CHANNELS and KEYWORDS):
    print("❌ Ошибка: не заданы все переменные окружения. Проверь API_ID, API_HASH, BOT_TOKEN, OWNER_ID, CHANNELS, KEYWORDS.")
    raise SystemExit(1)

# ==== Функция поиска ====
async def search_messages(client):
    found = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=CHECK_INTERVAL_HOURS + 1)

    for chat in CHANNELS:
        try:
            entity = await client.get_entity(chat)
        except Exception as e:
            print(f"⚠️ Не удалось получить чат {chat}: {e}")
            continue

        for kw in KEYWORDS:
            try:
                async for msg in client.iter_messages(entity, search=kw, limit=50):
                    if not msg.message:
                        continue
                    msg_date = msg.date.replace(tzinfo=timezone.utc)
                    if msg_date < cutoff:
                        continue

                    author = "—"
                    try:
                        sender = await msg.get_sender()
                        if sender:
                            author = (sender.first_name or '') + ' ' + (sender.last_name or '')
                            if getattr(sender, 'username', None):
                                author += f" (@{sender.username})"
                    except Exception:
                        pass

                    link = f"https://t.me/{getattr(entity, 'username', entity.id)}/{msg.id}" if getattr(entity, 'username', None) else ''
                    text = msg.message[:700]

                    found.append({
                        "chat": chat,
                        "author": author.strip(),
                        "text": text,
                        "link": link,
                        "date": msg_date
                    })

            except errors.FloodWaitError as e:
                print(f"⏳ FloodWait: ждём {e.seconds} секунд")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"Ошибка при поиске в {chat}: {e}")

    return found

# ==== Основной цикл ====
async def main():
    print("🚀 SurfFinder запущен!")
    client = TelegramClient("surf_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    while True:
        try:
            results = await search_messages(client)
            if results:
                message = f"🌊 Найдено {len(results)} сообщений о серфинге:\n\n"
                for r in results:
                    message += f"📍 {r['chat']}\n👤 {r['author']}\n🕒 {r['date'].strftime('%d.%m %H:%M')}\n\n{r['text']}\n🔗 {r['link']}\n\n"

                try:
                    await client.send_message(OWNER_ID, message)
                    print(f"✅ Отправлено {len(results)} результатов владельцу")
                except Exception as e:
                    print(f"Ошибка при отправке: {e}")
            else:
                print(f"🤙 Нет новых сообщений ({datetime.now().strftime('%H:%M:%S')})")

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")

        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 SurfFinder остановлен вручную.")
