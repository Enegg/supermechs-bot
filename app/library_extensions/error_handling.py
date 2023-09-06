import io
import logging
import traceback
import typing as t
from contextlib import suppress
from functools import partial

from disnake import (
    Client,
    Colour,
    CommandInteraction,
    Embed,
    Event,
    File,
    InteractionTimedOut,
    LocalizationProtocol,
)
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.ext.commands.common_bot_base import CommonBotBase
from disnake.utils import MISSING

from .pending import EmbedLimits
from .text_utils import SPACE, Markdown, localized_text

__all__ = ("setup_channel_logger",)


class SenderArguments(t.TypedDict, total=False):
    content: str | None
    embed: Embed
    embeds: list[Embed]
    file: File
    files: list[File]
    ephemeral: bool
    suppress_embeds: bool


def traceback_to_discord_file(traceback: str, /) -> File:
    bio = io.BytesIO(traceback.encode())
    return File(bio, "traceback.py", description="Traceback of a recent exception.")


def exception_to_message(exception: BaseException, /, limit: int) -> str | File:
    """Formats exception data and returns message content or file to send a message with.

    Formatted traceback is wrapped in a codeblock and appended to content if the resulting string
    stays under character limit, otherwise creates a File.
    """
    traceback_text = "".join(traceback.format_exception(exception))

    if len(traceback_text) + 10 > limit:
        return traceback_to_discord_file(traceback_text)

    return Markdown.codeblock(traceback_text, "py")


async def error_handler(
    channel: Messageable,
    i18n: LocalizationProtocol,
    logger: logging.Logger,
    /,
    inter: CommandInteraction,
    error: commands.CommandError,
) -> None:
    file = MISSING
    user_embed = MISSING

    if isinstance(error, commands.NotOwner):
        info = localized_text("This is a developer-only command.", "CMD_DEV", i18n, inter.locale)

    elif isinstance(error, (commands.UserInputError, commands.CheckFailure)):
        info = str(error)  # TODO: this isn't localized

    elif isinstance(error, commands.MaxConcurrencyReached):
        if error.number == 1 and error.per is commands.BucketType.user:
            info = localized_text(
                "Your previous invocation of this command has not finished executing.",
                "CMD_RUNNING",
                i18n,
                inter.locale,
            )

        else:
            info = str(error)

    else:
        arguments = ", ".join(
            f"`{option}: {value}`" for option, value in inter.filled_options.items()
        )
        exception = error.original if isinstance(error, commands.CommandInvokeError) else error
        metadata = (
            f"Place: `{inter.guild or inter.channel}`\n"
            f"User: {inter.author.mention} (`{inter.author.display_name}`)\n"
            f"Command: `/{inter.application_command.qualified_name}` {arguments}\n"
            f"Exception: `{exception}`"
        )
        embed = Embed(title="⚠️ Unhandled exception", color=Colour(0xFF0000))
        file_or_text = exception_to_message(exception, limit=EmbedLimits.description)

        if isinstance(file_or_text, str):
            embed.description = file_or_text
            embed.add_field(SPACE, metadata, inline=False)

        else:
            embed.description = metadata
            file = file_or_text

        if __debug__:
            info = None
            user_embed = embed
            logger.warning("Exception occured")

        else:
            await channel.send(embed=embed, file=file)
            logger.exception(metadata, exc_info=exception)

            info = localized_text(
                "Command executed with an error...", "CMD_ERROR", i18n, inter.locale
            )

    with suppress(InteractionTimedOut):
        await inter.send(info, file=file, embed=user_embed, ephemeral=not __debug__)


async def setup_channel_logger(client: Client, channel_id: int, logger: logging.Logger) -> None:
    """Creates an on_slash_command_error listener which sends tracebacks to selected channel."""
    assert isinstance(client, CommonBotBase)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        raise TypeError("Channel is not Messageable")

    client.add_listener(
        partial(error_handler, channel, client.i18n, logger), Event.slash_command_error
    )
