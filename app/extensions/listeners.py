import logging

from disnake import CommandInteraction
from disnake.ext import plugins

import config
from shared.metrics import add_invocation

plugin = plugins.Plugin(name="listeners", logger="event")
_LOG_READY = logging.getLogger("event.ready")


@plugin.listener()
async def on_ready() -> None:
    _LOG_READY.info(f"{plugin.bot.user.name} is ready")

    if __debug__:
        limit = plugin.bot.session_start_limit
        assert limit is not None
        _LOG_READY.info(
            f"Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:{config.DATE_FORMAT}})"
        )


@plugin.listener()
async def on_application_command(interaction: CommandInteraction, /) -> None:
    add_invocation(interaction.data.id, interaction.application_command.qualified_name)


setup, teardown = plugin.create_extension_handlers()
