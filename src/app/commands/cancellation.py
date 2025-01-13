from app.disnake_types import CommandInteraction
from discord.commands import CancelKey, get_key

CANCEL_BUTTON_ID = "cancelcmd"


def make_id(inter: CommandInteraction, /) -> str:
    key = get_key(inter)
    return f"{CANCEL_BUTTON_ID}:{key.user_id}:{key.command_id}"


def parse_id(custom_id: str, /) -> CancelKey:
    _, str_user_id, str_command_id = custom_id.split(":")
    return CancelKey(int(str_user_id), int(str_command_id))


def is_cancel_button(custom_id: str, /) -> bool:
    return custom_id.startswith(CANCEL_BUTTON_ID)
