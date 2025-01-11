from app.disnake_types import Bot
from disnake_plugins.plugin import Plugin, SlashCommandParams


def create_plugin(
    name: str, *, slash_command_attrs: SlashCommandParams | None = None
) -> Plugin[Bot]:
    _, _, name = name.rpartition(".")
    name = name.replace("_", "-").capitalize()
    return Plugin[Bot](name=name, logger="plugin", slash_command_attrs=slash_command_attrs)
