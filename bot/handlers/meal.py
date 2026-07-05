import json
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from bot.services.database import Database
from bot.models.recipe import Recipe, Ingredient
from bot.config import get_settings

labeler = BotLabeler()
user_states: dict[int, dict] = {}


def _get_db():
    return Database(get_settings().db_path)


def get_main_menu():
    return (
        Keyboard(inline=True)
        .add(Text("📋 Мой план"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("🛒 Список покупок"), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text("➕ Рецепт"), color=KeyboardButtonColor.SECONDARY)
        .add(Text("📖 Рецепты"), color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text("❓ Помощь"), color=KeyboardButtonColor.SECONDARY)
    )


DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MEALS = {"breakfast": "Завтрак", "lunch": "Обед", "dinner": "Ужин"}
MEAL_EMOJI = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}


@labeler.message(text="/start")
async def cmd_start(message: Message):
    await message.answer("🍽 Планировщик меню на неделю\n\nВыбери действие:", keyboard=get_main_menu())


@labeler.message(text="/help")
async def cmd_help(message: Message):
    await message.answer(
        "📝 Как пользоваться:\n\n"
        "1. Добавь рецепты (название + ингредиенты)\n"
        "2. Распланируй неделю\n"
        "3. Получи список покупок\n\n"
        "Команды:\n"
        "/start — меню\n"
        "/help — помощь",
        keyboard=get_main_menu()
    )


@labeler.message(text="📋 Мой план")
async def btn_plan(message: Message):
    db = _get_db()
    plan = await db.get_week_plan(message.from_user.id)

    if not plan:
        await message.answer("📋 План пока пуст.\nДобавь рецепты и распланируй неделю!", keyboard=get_main_menu())
        return

    text = "📋 План на неделю:\n\n"
    for day in DAYS:
        if day in plan:
            text += f"**{day}:**\n"
            for meal_type, meal in plan[day].items():
                emoji = MEAL_EMOJI.get(meal_type, "")
                text += f"  {emoji} {meal['name']} ({meal['calories']} ккал)\n"
            text += "\n"

    await message.answer(text, keyboard=get_main_menu())


@labeler.message(text="🛒 Список покупок")
async def btn_shopping(message: Message):
    db = _get_db()
    items = await db.get_shopping_list(message.from_user.id)

    if not items:
        await message.answer("🛒 Список пуст.\nСначала запланируй неделю!", keyboard=get_main_menu())
        return

    text = "🛒 Список покупок на неделю:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['amount']} {item['unit']}\n"

    await message.answer(text, keyboard=get_main_menu())


@labeler.message(text="➕ Рецепт")
async def btn_add_recipe(message: Message):
    user_states[message.from_user.id] = {"step": "name"}
    await message.answer(
        "➕ Добавь рецепт\n\nНапиши название блюда:",
        keyboard=Keyboard(inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
    )


@labeler.message(text="📖 Рецепты")
async def btn_recipes(message: Message):
    db = _get_db()
    recipes = await db.get_recipes(message.from_user.id)

    if not recipes:
        await message.answer("📖 Рецептов пока нет.", keyboard=get_main_menu())
        return

    kb = Keyboard(inline=True)
    for r in recipes:
        emoji = MEAL_EMOJI.get(r.meal_type, "")
        kb.add(Text(f"{emoji} {r.name}"), color=KeyboardButtonColor.SECONDARY)
        if recipes.index(r) % 2 == 1:
            kb.row()
    kb.row()
    kb.add(Text("◀️ Назад"), color=KeyboardButtonColor.NEGATIVE)

    await message.answer("📖 Твои рецепты:", keyboard=kb)


@labeler.message(text="❌ Отмена")
async def btn_cancel(message: Message):
    user_states.pop(message.from_user.id, None)
    await message.answer("Отменено.", keyboard=get_main_menu())


@labeler.message(text="◀️ Назад")
async def btn_back(message: Message):
    user_states.pop(message.from_user.id, None)
    await message.answer("Выбери действие:", keyboard=get_main_menu())


@labeler.message()
async def handle_text(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    state = user_states.get(user_id, {})

    if text.startswith("➕ ") and text[2:].strip() in [f"{MEAL_EMOJI[m]} {r}" for r in []]:
        return

    if "step" not in state:
        return

    db = _get_db()

    if state["step"] == "name":
        state["recipe_name"] = text
        state["step"] = "meal_type"
        kb = Keyboard(inline=True)
        kb.add(Text("🌅 Завтрак"), color=KeyboardButtonColor.POSITIVE)
        kb.add(Text("☀️ Обед"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("🌙 Ужин"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
        await message.answer(f"Блюдо: {text}\n\nВыбери тип приёма пищи:", keyboard=kb)

    elif state["step"] == "meal_type":
        meal_map = {"🌅 Завтрак": "breakfast", "☀️ Обед": "lunch", "🌙 Ужин": "dinner"}
        if text in meal_map:
            state["meal_type"] = meal_map[text]
            state["step"] = "ingredients"
            state["ingredients"] = []
            await message.answer(
                "📝 Добавь ингредиенты.\n\n"
                "Формат: **название — количество**\n"
                "Пример: курица — 500 г\n\n"
                "Когда закончиши, напиши **Готово**",
                keyboard=Keyboard(inline=True).add(Text("❌ Отмена"), color=KeyboardButtonColor.NEGATIVE)
            )

    elif state["step"] == "ingredients":
        if text.lower() == "готово":
            recipe = Recipe(
                user_id=user_id,
                name=state["recipe_name"],
                meal_type=state["meal_type"],
                ingredients=[Ingredient(**i) for i in state["ingredients"]],
            )
            await db.add_recipe(recipe)
            user_states.pop(user_id, None)
            await message.answer(f"✅ Рецепт «{recipe.name}» добавлен!", keyboard=get_main_menu())
        else:
            parts = text.split("—")
            if len(parts) == 2:
                name = parts[0].strip()
                amount_unit = parts[1].strip().split(" ", 1)
                amount = amount_unit[0]
                unit = amount_unit[1] if len(amount_unit) > 1 else ""
                state["ingredients"].append({"name": name, "amount": amount, "unit": unit})
                count = len(state["ingredients"])
                await message.answer(f"✅ {name} — {amount} {unit}\n\nИнгредиентов: {count}. Ещё или **Готово**?")
            else:
                await message.answer("Формат: название — количество\nПример: рис — 200 г")
