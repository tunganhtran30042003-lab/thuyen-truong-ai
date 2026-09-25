from typing import Optional
from config import CAPTAIN_KEYS


def get_captain_keys() -> set:
    return set(CAPTAIN_KEYS)


def is_valid_captain_key(key: Optional[str]) -> bool:
    if not key:
        return False
    keys = get_captain_keys()
    if not keys:
        return False
    return key in keys