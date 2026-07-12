import asyncio
from vkbottle import Bot

from bot.config import get_settings
from bot.services.database import Database
from bot.handlers import setup_handlers


async def main():
    settings = get_settings()
    bot = Bot(token=settings.vk_token)

    db = Database(settings.db_path)
    await db.init()

    setup_handlers(bot.labeler)

    print("🍽 VK Meal Planner Bot started!")
    await bot.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
