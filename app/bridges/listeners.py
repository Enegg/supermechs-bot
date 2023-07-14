import logging
import typing as t

from disnake import Client, CommandInteraction
from disnake.ext.commands.common_bot_base import CommonBotBase

from shared.metrics import add_invocation

ROOT_LOGGER = logging.getLogger()


async def on_ready(client: Client, /) -> None:
    ROOT_LOGGER.info(f"{client.user.name} is online")

    if __debug__:
        limit = client.session_start_limit
        assert limit is not None
        ROOT_LOGGER.info(
            f"Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
        )


async def on_application_command(interaction: CommandInteraction, /) -> None:
    data = interaction.data
    add_invocation(data.id, data.name)


def register_listeners(bot: CommonBotBase[t.Any], /) -> None:
    """Entry point for registering listeners."""
    bot.add_listener(on_ready)
    bot.add_listener(on_application_command)
