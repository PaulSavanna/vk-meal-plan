from vkbottle.bot import BotLabeler
from bot.handlers.meal import labeler as meal_labeler


def setup_handlers(dp: BotLabeler):
    dp.load(meal_labeler)
