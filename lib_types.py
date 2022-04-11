from __future__ import annotations

import typing as t

import disnake
from disnake.ext import commands

if t.TYPE_CHECKING:
    from bot import SMBot


class MessageInteraction(disnake.MessageInteraction):
    bot: SMBot


class ApplicationCommandInteraction(disnake.ApplicationCommandInteraction):
    bot: SMBot


class ForbiddenChannel(commands.CheckFailure):
    """Exception raised when command is used from invalid channel."""

    def __init__(self, message: str | None = None, *args: t.Any) -> None:
        super().__init__(message=message or "You cannot use this command here.", *args)
