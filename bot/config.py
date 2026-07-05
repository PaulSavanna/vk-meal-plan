from dataclasses import dataclass
from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Settings:
    vk_token: str
    db_path: str = "meal_plan.db"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(vk_token=os.environ.get("VK_TOKEN", "test-token"))


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        load_dotenv()
        _settings = Settings(vk_token=os.environ.get("VK_TOKEN", "test-token"))
    return _settings
