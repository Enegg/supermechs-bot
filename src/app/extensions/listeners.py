import logging

from disnake import CommandInteraction
from disnake_plugins import Plugin

from app.bridges import add_invocation
from app.core import CONFIG

plugin = Plugin(name="listeners", logger=__name__)
_EVENTS_LOG = logging.getLogger("event")


@plugin.listener()
async def on_ready() -> None:
    _EVENTS_LOG.info("%s is ready", plugin.bot.user.name)

    if __debug__:
        limit = plugin.bot.session_start_limit
        assert limit is not None
        _EVENTS_LOG.info(
            f"Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:{CONFIG.date_format}})"
        )


@plugin.listener()
async def on_application_command(inter: CommandInteraction, /) -> None:
    command_name = inter.application_command.qualified_name
    _EVENTS_LOG.debug("Slash command invoked: /%s", command_name)
    add_invocation(inter.data.id, command_name)


setup, teardown = plugin.create_extension_handlers()
