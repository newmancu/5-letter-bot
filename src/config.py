from dataclasses import dataclass
from functools import cache
from os import getenv


@dataclass
class Settings:
    token: str
    max_tries: int


@cache
def get_settings() -> Settings:
    return Settings(
        token=getenv("token"), max_tries=int(getenv("game_max_tries", "5"))
    )
