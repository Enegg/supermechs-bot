"""Collection of functions related to (discord specific) markdown formatting."""

from enum import StrEnum
from typing import Any, Protocol, override

import disnake
from disnake.utils import format_dt

__all__ = ("codeblock", "command_mention", "format_dt", "hyperlink")


def hyperlink(text: str, url: str) -> str:
    """Return a hyperlink to a URL."""
    return f"[{text}]({url})"


def codeblock(text: str, lang: str = "") -> str:
    """Return text formatted with a codeblock."""
    return f"```{lang}\n{text}```"


class Commandish(Protocol):
    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...


def command_mention(command: Commandish | disnake.CommandInteraction[Any], /) -> str:
    """Return a string mentioning a slash command."""
    if isinstance(command, disnake.CommandInteraction):
        return f"</{command.application_command.qualified_name}:{command.data.id}>"
    return f"</{command.name}:{command.id}>"


class GuildNavigation(StrEnum):
    customize = "customize"
    browse = "browse"
    guide = "guide"
    linked_roles = "linked-roles"

    @override
    def __str__(self) -> str:
        return f"<id:{self.value}>"

    @staticmethod
    def linked_role(role: disnake.abc.Snowflake, /) -> str:
        return f"<id:linked-roles:{role.id}>"
