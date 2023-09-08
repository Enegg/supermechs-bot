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

from .pending import EmbedLimits
from .text_utils import SPACE, Markdown, localized_text

__all__ = ("setup_channel_logger",)


class SenderKeywords(t.TypedDict, total=False):
    content: str
    embed: Embed
    file: File
    suppress_embeds: bool


I18nGetter = t.Callable[[str, str], str]


def traceback_to_discord_file(traceback: str, /) -> File:
    bio = io.BytesIO(traceback.encode())
    return File(bio, "traceback.py", description="Traceback of a recent exception.")


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> SenderKeywords:
    arguments = ", ".join(
        f"`{option}: {value}`" for option, value in inter.filled_options.items()
    )
    metadata = (
        f"Place: `{inter.guild or inter.channel}`\n"
        f"User: {inter.author.mention} (`{inter.author.display_name}`)\n"
        f"Command: `/{inter.application_command.qualified_name}` {arguments}\n"
        f"Exception: `{type(exc).__name__}: {exc}`"
    )
    embed = Embed(title="⚠️ Unhandled exception", color=Colour(0xFF0000))
    params: SenderKeywords = {"embed": embed}

    traceback_text = "".join(traceback.format_exception(exc))

    if len(traceback_text) + 10 > EmbedLimits.description:
        params["file"] = traceback_to_discord_file(traceback_text)
        embed.description = metadata

    else:
        embed.description = Markdown.codeblock(traceback_text, "py")
        embed.add_field(SPACE, metadata, inline=False)

    return params


def handle_informational_exception(
    exc: commands.CommandError,
    localize: I18nGetter
) -> str | None:
    if isinstance(exc, commands.NotOwner):
        info = localize("This is a developer-only command.", "CMD_DEV")

    elif isinstance(exc, (commands.UserInputError, commands.CheckFailure)):
        info = str(exc)  # TODO: this isn't localized

    elif isinstance(exc, commands.MaxConcurrencyReached):
        if exc.number == 1 and exc.per is commands.BucketType.user:
            info = localize(
                "Your previous invocation of this command has not finished executing.",
                "CMD_RUNNING",
            )

        else:
            info = str(exc)

    else:
        return None

    return info


def handle_timeout(exc: commands.CommandError, localize: I18nGetter) -> str | None:
    if isinstance(exc, commands.CommandInvokeError) and isinstance(exc.original, TimeoutError):
        return localize("Command execution timed out.", "CMD_TIMEOUT")

    return None


async def error_handler(
    channel: Messageable,
    i18n: LocalizationProtocol,
    logger: logging.Logger,
    /,
    inter: CommandInteraction,
    error: commands.CommandError,
) -> None:
    localize: I18nGetter = partial(localized_text, i18n=i18n, locale=inter.locale)

    if content := handle_informational_exception(error, localize):
        with suppress(InteractionTimedOut):
            await inter.send(content, ephemeral=True)
        return

    if content := handle_timeout(error, localize):
        with suppress(InteractionTimedOut):
            await inter.send(content, ephemeral=True)
        logger.warning("Command %s timed out", inter.application_command.qualified_name)
        return

    exc = error.original if isinstance(error, commands.CommandInvokeError) else error
    params = exception_to_message(exc, inter)

    if __debug__:
        logger.warning("Exception occured in %s", inter.application_command.qualified_name)
        user_params = params

    else:
        logger.exception("Unhandled exception:", exc_info=exc)
        await channel.send(**params)
        user_params: SenderKeywords = {
            "content": localize("Command executed with an error...", "CMD_ERROR")
        }

    with suppress(InteractionTimedOut):
        await inter.send(**user_params, ephemeral=not __debug__)


async def setup_channel_logger(client: Client, channel_id: int, logger: logging.Logger) -> None:
    """Creates an on_slash_command_error listener which sends tracebacks to selected channel."""
    assert isinstance(client, CommonBotBase)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        raise TypeError("Channel is not Messageable")

    client.add_listener(
        partial(error_handler, channel, client.i18n, logger), Event.slash_command_error
    )
