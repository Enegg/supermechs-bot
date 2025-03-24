from app.disnake_types import Bot, CommandInteraction
from discord.commands import CancelToken, CustomEvent, cancel_command_for, get_cancel_token
from disnake import Event

from app import i18n, ui

CANCEL_BUTTON_ID = "cancelcmd"


def get_cancel_button_id(inter: CommandInteraction, /) -> str:
    key = get_cancel_token(inter)
    return f"{CANCEL_BUTTON_ID}:{key.user_id:x}:{key.command_id:x}"


def parse_cancel_token(custom_id: str, /) -> CancelToken:
    _, str_user_id, str_command_id = custom_id.split(":")
    return CancelToken(int(str_user_id, 16), int(str_command_id, 16))


def is_cancel_button(custom_id: str, /) -> bool:
    return custom_id.startswith(CANCEL_BUTTON_ID)


def cancel_button(inter: CommandInteraction, gettext: i18n.GetText) -> ui.ActionButton:
    return ui.ActionButton(
        custom_id=get_cancel_button_id(inter),
        style=ui.ButtonStyle.red,
        label=gettext("ui-cmd-cancel-button"),
        emoji="🛑",
    )


async def on_cancel_button(inter: ui.MessageInteraction, /) -> None:
    if not is_cancel_button(inter.data.custom_id):
        return

    await inter.response.defer()
    await inter.delete_original_response()
    cancel_command_for(parse_cancel_token(inter.data.custom_id))
    # NOTE: concrete command classes override .invoke
    # TODO: somehow invoke command callback using MessageInteraction


async def on_concurrent_command(inter: CommandInteraction) -> None:
    gettext = i18n.get_gettext(inter.locale)
    button = cancel_button(inter, gettext)
    await inter.response.send_message(gettext("command-running"), components=button, ephemeral=True)


def setup(bot: Bot) -> None:
    bot.add_listener(on_cancel_button, Event.button_click)
    bot.add_listener(on_concurrent_command, CustomEvent.cancel.listener_name)
