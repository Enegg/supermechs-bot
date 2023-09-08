import logging
import typing as t
from functools import partial

from disnake import Client, CommandInteraction, Event
from disnake.ext.commands.common_bot_base import CommonBotBase

from config import DATE_FORMAT
from shared.metrics import add_invocation

ROOT_LOGGER = logging.getLogger()


async def on_ready(client: Client, /) -> None:
    ROOT_LOGGER.info(f"{client.user.name} is online")

    if __debug__:
        limit = client.session_start_limit
        assert limit is not None
        ROOT_LOGGER.info(
            f"Session #{limit.total - limit.remaining}/{limit.total}"
            f" (expires {limit.reset_time:{DATE_FORMAT}})"
        )


async def on_application_command(interaction: CommandInteraction, /) -> None:
    add_invocation(interaction.data.id, interaction.application_command.qualified_name)


def register_listeners(bot: CommonBotBase[t.Any], /) -> None:
    """Entry point for registering listeners."""
    assert isinstance(bot, Client)
    bot.add_listener(partial(on_ready, bot), Event.ready)
    bot.add_listener(on_application_command)
