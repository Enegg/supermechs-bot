import logging

from app.disnake_types import CommandInteraction
from disnake import Event

from app.bridges.telemetry import command_tracker
from app.plugins_factory import create_plugin

plugin = create_plugin(__name__)
_LOG = logging.getLogger("event")


@plugin.listener(Event.ready)
async def on_ready() -> None:
    limit = plugin.bot.session_start_limit
    assert limit is not None
    _LOG.info(
        f"Username: {plugin.bot.user.name};"
        f" Session #{limit.total - limit.remaining}/{limit.total}"
        f" (expires {limit.reset_time:%d.%m.%Y %H:%M:%S})"
    )


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
    command_tracker.add_invocation(inter)


@plugin.listener(Event.slash_command_completion)
async def on_slash_command_completion(inter: CommandInteraction, /) -> None:
    command_name = inter.application_command.qualified_name
    result = "failed" if inter.command_failed else "finished"
    _LOG.info("Command by %s %s: /%s", inter.author, result, command_name)


setup, teardown = plugin.create_extension_handlers()
