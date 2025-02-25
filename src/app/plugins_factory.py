from app.disnake_types import Bot
from disnake import Permissions
from disnake_plugins.plugin import Plugin

from app.core import CONFIG


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
