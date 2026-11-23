from collections import abc

from disnake import Permissions
from disnake_plugins.plugin import AnyBot, Plugin

from app.core.config import CONFIG
from app.typeshed import Bot

type SetupFn[BotT: AnyBot] = abc.Callable[[BotT], abc.Awaitable[None]]


def _extract_plugin_name(name: str, /) -> str:
    _, _, name = name.rpartition(".")
    return name.replace("_", "-").capitalize()


def create_plugin(name: str, /) -> Plugin[Bot]:
    return Plugin[Bot](name=_extract_plugin_name(name), logger="plugin")


def create_dev_plugin(name: str, /) -> Plugin[Bot]:
    return Plugin[Bot](
        name=_extract_plugin_name(name),
        logger="dev-plugin",
        slash_command_attrs={
            "guild_ids": CONFIG.test_guild_ids,
            "default_member_permissions": Permissions(administrator=True),
        },
    )


def create_plugin_handlers[BotT: AnyBot](
    plugin: Plugin[BotT], /
) -> tuple[SetupFn[BotT], SetupFn[BotT]]:
    return plugin.load, plugin.unload
