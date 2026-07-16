import pytest
from bot.services.database import Database
from bot.models.recipe import Recipe, Ingredient


@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path / "test.db"))


@pytest.mark.asyncio
async def test_init_db(db):
    await db.init()
    recipes = await db.get_recipes(123)
    assert recipes == []


@pytest.mark.asyncio
async def test_add_recipe(db):
    await db.init()
    recipe = Recipe(
        user_id=123, name="Овсянка", meal_type="breakfast", calories=300,
        ingredients=[Ingredient(name="овсянка", amount="100", unit="г"), Ingredient(name="молоко", amount="200", unit="мл")],
    )
    recipe_id = await db.add_recipe(recipe)

    recipes = await db.get_recipes(123)
    assert len(recipes) == 1
    assert recipes[0].name == "Овсянка"
    assert len(recipes[0].ingredients) == 2


@pytest.mark.asyncio
async def test_get_recipes_by_type(db):
    await db.init()
    await db.add_recipe(Recipe(user_id=123, name="Овсянка", meal_type="breakfast"))
    await db.add_recipe(Recipe(user_id=123, name="Салат", meal_type="lunch"))

    breakfast = await db.get_recipes(123, "breakfast")
    assert len(breakfast) == 1
    assert breakfast[0].name == "Овсянка"


@pytest.mark.asyncio
async def test_week_plan(db):
    await db.init()
    recipe = Recipe(user_id=123, name="Каша", meal_type="breakfast",
                    ingredients=[Ingredient(name="гречка", amount="150", unit="г")])
    recipe_id = await db.add_recipe(recipe)

    await db.set_week_plan(123, "Пн", "breakfast", recipe_id)
    plan = await db.get_week_plan(123)

    assert "Пн" in plan
    assert "breakfast" in plan["Пн"]
    assert plan["Пн"]["breakfast"]["name"] == "Каша"


@pytest.mark.asyncio
async def test_shopping_list(db):
    await db.init()
    r1 = Recipe(user_id=123, name="Овсянка", meal_type="breakfast",
                ingredients=[Ingredient(name="овсянка", amount="100", unit="г")])
    r2 = Recipe(user_id=123, name="Плов", meal_type="dinner",
                ingredients=[Ingredient(name="рис", amount="300", unit="г"), Ingredient(name="овсянка", amount="50", unit="г")])
    id1 = await db.add_recipe(r1)
    id2 = await db.add_recipe(r2)

    await db.set_week_plan(123, "Пн", "breakfast", id1)
    await db.set_week_plan(123, "Пн", "dinner", id2)

    items = await db.get_shopping_list(123)
    names = {i["name"] for i in items}
    assert "овсянка" in names
    assert "рис" in names


@pytest.mark.asyncio
async def test_delete_recipe(db):
    await db.init()
    recipe = Recipe(user_id=123, name="Тест", meal_type="lunch")
    recipe_id = await db.add_recipe(recipe)
    await db.delete_recipe(recipe_id, 123)
    recipes = await db.get_recipes(123)
    assert len(recipes) == 0


@pytest.mark.asyncio
async def test_empty_week_menu_shopping_list(db):
    """Empty weekly menu should return empty shopping list without errors."""
    await db.init()
    items = await db.get_shopping_list(999)
    assert items == []


@pytest.mark.asyncio
async def test_duplicate_ingredients_summed(db):
    """Duplicate ingredients across dishes should be summed numerically, not concatenated as strings."""
    await db.init()
    r1 = Recipe(user_id=123, name="Овсянка", meal_type="breakfast",
                ingredients=[Ingredient(name="овсянка", amount="100", unit="г")])
    r2 = Recipe(user_id=123, name="Каша", meal_type="lunch",
                ingredients=[Ingredient(name="овсянка", amount="50", unit="г")])
    id1 = await db.add_recipe(r1)
    id2 = await db.add_recipe(r2)

    await db.set_week_plan(123, "Пн", "breakfast", id1)
    await db.set_week_plan(123, "Пн", "lunch", id2)

    items = await db.get_shopping_list(123)
    oats = [i for i in items if i["name"] == "овсянка"]
    assert len(oats) == 1
    assert oats[0]["amount"] == 150
    assert oats[0]["unit"] == "г"
