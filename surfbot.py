import os
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, AccessTokenExpiredError, RPCError

# === Загрузка переменных окружения (Render Dashboard → Environment) ===
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("🌴 Проверка переменных окружения:")
print(f"API_ID: {API_ID}")
print(f"API_HASH: {'✅ есть' if API_HASH else '❌ нет'}")
print(f"BOT_TOKEN: {'✅ есть' if BOT_TOKEN else '❌ нет'}")
print(f"CHAT_ID: {CHAT_ID if CHAT_ID else '❌ нет'}")
print("=====================================")

if not all([API_ID, API_HASH, BOT_TOKEN, CHAT_ID]):
    print("❌ Ошибка: не заданы все переменные окружения!")
    print("Проверь Render → Environment → API_ID, API_HASH, BOT_TOKEN, CHAT_ID")
    exit(1)

API_ID = int(API_ID)

# === Основная функция ===
async def start_bot():
    client = TelegramClient("surf_session", API_ID, API_HASH)

    try:
        print(f"\n🌊 [{datetime.now().strftime('%H:%M:%S')}] Подключаемся к Telegram...")
        await client.start(bot_token=BOT_TOKEN)

        me = await client.get_me()
        print(f"✅ Бот @{me.username} запущен и готов к волнам.")

        # Сообщаем в Telegram, что бот стартовал
        start_msg = f"🚀 Бот @{me.username} запущен и онлайн 🌴\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        await client.send_message(CHAT_ID, start_msg)
        print("📩 Уведомление о старте отправлено в Telegram.")

        # === Основной цикл ===
        while True:
            try:
                # Каждые 60 минут сообщает, что жив
                await asyncio.sleep(3600)
                await client.send_message(CHAT_ID, f"🌊 Всё под контролем! Бот онлайн ✅\n{datetime.now().strftime('%H:%M:%S')}")
                print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] Сообщение о статусе отправлено.")

            except FloodWaitError as e:
                print(f"⚠️ FloodWait: ждём {e.seconds} секунд.")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"💥 Ошибка в цикле: {e}")
                await client.send_message(CHAT_ID, f"⚠️ Ошибка в работе бота:\n`{type(e).__name__}: {e}`\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                await asyncio.sleep(60)

    except FloodWaitError as e:
        print(f"⏳ FloodWait: пауза {e.seconds} секунд.")
        await asyncio.sleep(e.seconds + 5)
        await start_bot()

    except AccessTokenExpiredError:
        print("❌ Токен бота просрочен. Обнови его через @BotFather.")
        try:
            await client.send_message(CHAT_ID, "❌ Токен бота истёк. Обнови его в @BotFather.")
        except:
            pass
        await asyncio.sleep(3600)
        await start_bot()

    except Exception as e:
        print(f"💥 Критическая ошибка: {type(e).__name__}: {e}")
        try:
            await client.send_message(CHAT_ID, f"💥 Критическая ошибка:\n`{type(e).__name__}: {e}`\n⏰ {datetime.now().strftime('%H:%M:%S')}")
        except:
            print("⚠️ Не удалось отправить сообщение об ошибке.")
        await asyncio.sleep(120)
        await start_bot()

    finally:
        await client.disconnect()
        print("🔌 Соединение закрыто.")


# === Точка входа ===
if __name__ == "__main__":
    print("🚀 Запуск SurfHunter Bot...")
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("🛑 Остановлено вручную.")
    except Exception as e:
        print(f"⚠️ Глобальная ошибка: {e}")