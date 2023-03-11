from pyrogram.types import InlineKeyboardButton
from typing import NamedTuple

class CachedMarkup(NamedTuple):
    buttons: list[list[InlineKeyboardButton]]
    user_id: int

