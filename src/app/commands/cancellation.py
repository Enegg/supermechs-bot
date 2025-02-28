from app.disnake_types import CommandInteraction
from discord.commands import CancelToken, get_cancel_token

CANCEL_BUTTON_ID = "cancelcmd"


def get_cancel_button_id(inter: CommandInteraction, /) -> str:
    key = get_cancel_token(inter)
    return f"{CANCEL_BUTTON_ID}:{key.user_id:x}:{key.command_id:x}"


def parse_cancel_token(custom_id: str, /) -> CancelToken:
    _, str_user_id, str_command_id = custom_id.split(":")
    return CancelToken(int(str_user_id, 16), int(str_command_id, 16))


def is_cancel_button(custom_id: str, /) -> bool:
    return custom_id.startswith(CANCEL_BUTTON_ID)
