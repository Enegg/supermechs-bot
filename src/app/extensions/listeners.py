import logging

from discord.commands import cancel_for
from disnake import CommandInteraction, Event
from disnake_plugins import Plugin

from app.bridges import add_invocation, ui
from app.bridges.cancellation import is_cancel_button, parse_id

plugin = Plugin(name="listeners", logger="ext")
_LOG = logging.getLogger("event")


@plugin.listener(Event.ready)
async def on_ready() -> None:
    if __debug__:
        limit = plugin.bot.session_start_limit
        assert limit is not None
        _LOG.info(
            f"Username: {plugin.bot.user.name};"
            f" Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )

    else:
        _LOG.info(f"Username: {plugin.bot.user.name}")


@plugin.listener(Event.slash_command)
async def on_slash_command(inter: CommandInteraction, /) -> None:
    command_name = inter.application_command.qualified_name
    _LOG.info(
        "%s (%d): /%s",
        inter.author,
        inter.author.id,
        command_name,
        extra={"filled_options": inter.filled_options},
    )
    add_invocation(inter.data.id, command_name)


@plugin.listener(Event.button_click)
async def on_cancel_button(inter: ui.MessageInteraction, /) -> None:
    if not is_cancel_button(inter.data.custom_id):
        return

    await inter.response.defer()
    await inter.delete_original_response()
    cancel_for(parse_id(inter.data.custom_id))


@plugin.listener(Event.slash_command_completion)
async def on_slash_command_completion(inter: CommandInteraction, /) -> None:
    command_name = inter.application_command.qualified_name
    result = "failed" if inter.command_failed else "finished"
    _LOG.info("Command by %s %s: /%s", inter.author, result, command_name)


setup, teardown = plugin.create_extension_handlers()
