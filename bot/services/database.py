import aiosqlite
import json
from bot.models.recipe import Recipe, Ingredient


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    meal_type TEXT DEFAULT 'breakfast',
                    calories INTEGER DEFAULT 0,
                    ingredients TEXT DEFAULT '[]'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS week_plan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    day_name TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    recipe_id INTEGER,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
                )
            """)
            await db.commit()

    async def add_recipe(self, recipe: Recipe) -> int:
        ingredients_json = json.dumps([{"name": i.name, "amount": i.amount, "unit": i.unit} for i in recipe.ingredients])
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO recipes (user_id, name, meal_type, calories, ingredients) VALUES (?, ?, ?, ?, ?)",
                (recipe.user_id, recipe.name, recipe.meal_type, recipe.calories, ingredients_json),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_recipes(self, user_id: int, meal_type: str | None = None) -> list[Recipe]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if meal_type:
                async with db.execute(
                    "SELECT * FROM recipes WHERE user_id = ? AND meal_type = ?", (user_id, meal_type)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("SELECT * FROM recipes WHERE user_id = ?", (user_id,)) as cursor:
                    rows = await cursor.fetchall()

            return [
                Recipe(
                    id=row["id"], user_id=row["user_id"], name=row["name"],
                    meal_type=row["meal_type"], calories=row["calories"],
                    ingredients=[Ingredient(**i) for i in json.loads(row["ingredients"])],
                )
                for row in rows
            ]

    async def delete_recipe(self, recipe_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id))
            await db.commit()

    async def set_week_plan(self, user_id: int, day_name: str, meal_type: str, recipe_id: int | None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM week_plan WHERE user_id = ? AND day_name = ? AND meal_type = ?",
                (user_id, day_name, meal_type),
            )
            if recipe_id:
                await db.execute(
                    "INSERT INTO week_plan (user_id, day_name, meal_type, recipe_id) VALUES (?, ?, ?, ?)",
                    (user_id, day_name, meal_type, recipe_id),
                )
            await db.commit()

    async def get_week_plan(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT wp.day_name, wp.meal_type, r.name as recipe_name, r.calories, r.ingredients
                   FROM week_plan wp
                   LEFT JOIN recipes r ON wp.recipe_id = r.id
                   WHERE wp.user_id = ?
                   ORDER BY 
                     CASE wp.day_name 
                       WHEN 'Пн' THEN 1 WHEN 'Вт' THEN 2 WHEN 'Ср' THEN 3 
                       WHEN 'Чт' THEN 4 WHEN 'Пт' THEN 5 WHEN 'Сб' THEN 6 WHEN 'Вс' THEN 7 
                     END,
                     CASE wp.meal_type 
                       WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2 WHEN 'dinner' THEN 3 
                     END""",
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

            plan = {}
            for row in rows:
                day = row["day_name"]
                if day not in plan:
                    plan[day] = {}
                plan[day][row["meal_type"]] = {
                    "name": row["recipe_name"],
                    "calories": row["calories"],
                    "ingredients": json.loads(row["ingredients"]) if row["ingredients"] else [],
                }
            return plan

    async def get_shopping_list(self, user_id: int) -> list[dict]:
        plan = await self.get_week_plan(user_id)
        ingredients = {}

        for day, meals in plan.items():
            for meal_type, meal in meals.items():
                if meal and meal.get("ingredients"):
                    for ing in meal["ingredients"]:
                        key = ing["name"].lower()
                        if key in ingredients:
                            try:
                                ingredients[key]["amount"] += float(ing["amount"])
                            except (ValueError, TypeError):
                                ingredients[key]["amount"] = f"{ingredients[key]['amount']} + {ing['amount']}"
                        else:
                            try:
                                amount = float(ing["amount"])
                            except (ValueError, TypeError):
                                amount = ing["amount"]
                            ingredients[key] = {
                                "name": ing["name"],
                                "amount": amount,
                                "unit": ing.get("unit", ""),
                            }

        return list(ingredients.values())
