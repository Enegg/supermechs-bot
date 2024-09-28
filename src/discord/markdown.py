"""Collection of functions related to (discord specific) markdown formatting."""

from typing import Protocol

from disnake.utils import format_dt

__all__ = ("codeblock", "command_mention", "format_dt", "hyperlink", "strip_codeblock")


def hyperlink(text: str, url: str) -> str:
    """Return a hyperlink to a URL."""
    return f"[{text}]({url})"


def codeblock(text: str, lang: str = "") -> str:
    """Return text formatted with a codeblock."""
    return f"```{lang}\n{text}```"


def strip_codeblock(text: str, /) -> str:
    """Return text stripped from codeblock syntax."""
    text = text.removeprefix("```").removesuffix("```")
    lang, sep, stripped = text.partition("\n")

    # coffeescript seems to be the longest lang name discord accepts
    if sep and len(lang) <= len("coffeescript"):
        return stripped

    return text


class Commandish(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def name(self) -> str: ...


def command_mention(command: Commandish, /) -> str:
    """Return a string mentioning a slash command."""
    return f"</{command.name}:{command.id}>"
