from dataclasses import dataclass, field


@dataclass
class Ingredient:
    name: str
    amount: str
    unit: str = ""


@dataclass
class Recipe:
    id: int | None = None
    user_id: int = 0
    name: str = ""
    meal_type: str = "breakfast"
    calories: int = 0
    ingredients: list[Ingredient] = field(default_factory=list)


@dataclass
class DayPlan:
    day_name: str = ""
    breakfast: Recipe | None = None
    lunch: Recipe | None = None
    dinner: Recipe | None = None
