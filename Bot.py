from telethon import TelegramClient, events
import asyncio
import logging
import time

# ===================== CONFIG ===================== #
API_ID = 1234567                    # Ваш API ID с my.telegram.org
API_HASH = "abcdef12345"            # Ваш API HASH
BOT_TOKEN = "123456:ABC-DEF1234ghIkl"  # Токен бота от @BotFather
SESSION_NAME = "parser_bot"         # Имя файла сессии (без расширения)
MAX_PARTICIPANTS = 10000            # Максимальное количество участников для парсинга
# ================= END CONFIG ===================== #

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParserBot:
    def __init__(self):
        self.is_parsing = False
        self.current_task = None
        self.client = TelegramClient(f"{SESSION_NAME}_user", API_ID, API_HASH)
        self.bot = TelegramClient(f"{SESSION_NAME}_bot", API_ID, API_HASH)

    async def init_clients(self):
        # Запускаем клиент пользователя
        await self.client.start()
        logger.info("User client started")
        
        # Запускаем бота
        await self.bot.start(bot_token=BOT_TOKEN)
        logger.info("Bot client started")
        
        # Регистрация обработчиков
        self.register_handlers()

    def register_handlers(self):
        @self.bot.on(events.NewMessage(pattern=r'^/start$'))
        async def start_handler(event):
            await event.respond(
                "🤖 **Бот для парсинга участников чатов**\n\n"
                "Просто напишите:\n"
                "`/parse @username` - парсинг указанного чата\n"
                "`/parse` - парсинг текущего чата\n"
                "`/stop` - остановить парсинг\n"
                "`/status` - статус работы\n\n"
                f"⚠ Лимит участников: {MAX_PARTICIPANTS}"
            )

        @self.bot.on(events.NewMessage(pattern=r'^/parse(?: |$)(.+)?$'))
        async def parse_handler(event):
            if self.is_parsing:
                await event.respond("⚠ Уже идет парсинг. Дождитесь завершения или введите /stop")
                return
            
            chat_input = event.pattern_match.group(1)
            if not chat_input:
                if event.is_private:
                    await event.respond("❌ Укажите чат для парсинга (/parse @username)")
                    return
                chat_input = event.chat.username or f"-100{event.chat.id}"
            
            try:
                msg = await event.respond(f"🔄 Начинаю парсинг чата {chat_input}...")
                self.is_parsing = True
                self.current_task = asyncio.create_task(self.parse_members(chat_input, event))
                await self.current_task
            except Exception as e:
                await msg.edit(f"❌ Ошибка: {str(e)}")

        @self.bot.on(events.NewMessage(pattern=r'^/stop$'))
        async def stop_handler(event):
            if self.is_parsing:
                self.is_parsing = False
                if self.current_task:
                    self.current_task.cancel()
                await event.respond("⏹ Парсинг остановлен")
            else:
                await event.respond("ℹ Нет активных задач парсинга")

        @self.bot.on(events.NewMessage(pattern=r'^/status$'))
        async def status_handler(event):
            if self.is_parsing:
                await event.respond("🔄 Парсинг в процессе...")
            else:
                await event.respond("💤 Бот свободен, можно начинать парсинг")

    async def parse_members(self, chat_id, event):
        try:
            participants = []
            counter = 0
            last_report = 0
            
            async for user in self.client.iter_participants(chat_id, aggressive=True):
                if not self.is_parsing:
                    await event.respond("⏹ Парсинг остановлен")
                    return
                
                participants.append(user)
                counter += 1
                
                if counter % 100 == 0 or time.time() - last_report > 5:
                    last_report = time.time()
                    await event.respond(f"⏳ Собрано {counter} участников...")
                
                if counter >= MAX_PARTICIPANTS:
                    await event.respond(f"⚠ Достигнут лимит в {MAX_PARTICIPANTS} участников")
                    break
            
            if not participants:
                await event.respond("❌ Не удалось получить участников")
                return
            
            filename = f"members_{chat_id.replace('@', '')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for user in participants:
                    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                    username = f"@{user.username}" if user.username else "нет"
                    phone = f" | Телефон: {user.phone}" if user.phone else ""
                    f.write(f"ID: {user.id} | Имя: {name} | Ник: {username}{phone}\n")
            
            await event.respond(
                f"✅ Готово! Сохранено {len(participants)} участников\n"
                f"Файл: `{filename}`",
                file=filename
            )
            
        except Exception as e:
            await event.respond(f"❌ Ошибка: {str(e)}")
        finally:
            self.is_parsing = False
            self.current_task = None

    async def run(self):
        await self.init_clients()
        logger.info("Бот запущен и готов к работе!")
        await self.bot.run_until_disconnected()

async def main():
    bot = ParserBot()
    await bot.run()

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
    finally:
        logger.info("Завершение работы")
