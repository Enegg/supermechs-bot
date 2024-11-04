import logging

from discord.commands import cancel_for
from disnake import CommandInteraction, Event
from disnake_plugins import Plugin

from app.bridges import add_invocation, ui
from app.bridges.cancellation import is_cancel_button, parse_id
from app.core import CONFIG

plugin = Plugin(name="listeners", logger="ext")
_EVENTS_LOG = logging.getLogger("event")


@plugin.listener(Event.ready)
async def on_ready() -> None:
    _EVENTS_LOG.info("%s is ready", plugin.bot.user.name)

    if __debug__:
        limit = plugin.bot.session_start_limit
        assert limit is not None
        _EVENTS_LOG.info(
            f"Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:{CONFIG.date_format}})"
        )


@plugin.listener(Event.slash_command)
async def on_slash_command(inter: CommandInteraction, /) -> None:
    command_name = inter.application_command.qualified_name
    _EVENTS_LOG.debug("Slash command invoked: /%s", command_name)
    add_invocation(inter.data.id, command_name)


@plugin.listener(Event.button_click)
async def on_cancel_button(inter: ui.MessageInteraction, /) -> None:
    if not is_cancel_button(inter.data.custom_id):
        return

    await inter.response.defer()
    await inter.delete_original_response()
    cancel_for(parse_id(inter.data.custom_id))


setup, teardown = plugin.create_extension_handlers()
