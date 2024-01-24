import logging
import os
import traceback
import typing
from contextlib import suppress
from functools import partial

from disnake import Client, Colour, CommandInteraction, Embed, Event, File, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.ext.commands.common_bot_base import CommonBotBase

import i18n

from .file_utils import text_to_file
from .limits import EmbedLimits
from .text_utils import SPACE, Markdown

__all__ = ("setup_channel_logger",)


class SenderKeywords(typing.TypedDict, total=False):
    content: str
    embed: Embed
    file: File
    suppress_embeds: bool


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> SenderKeywords:
    arguments = ", ".join(f"`{option}: {value}`" for option, value in inter.filled_options.items())
    header = (
        f"Place: `{inter.guild or inter.channel}`\n"
        f"User: {inter.author.mention} (`{inter.author.display_name}`)\n"
        f"Command: `/{inter.application_command.qualified_name}` {arguments}\n"
        f"Exception: `{type(exc).__name__}: {exc}`"
    )
    embed = Embed(title="⚠️ Unhandled exception", color=Colour(0xFF0000))
    params: SenderKeywords = {"embed": embed}

    traceback_text = "".join(traceback.format_exception(exc))
    traceback_text = traceback_text.replace(os.getcwd(), ".")  # noqa: PTH109

    if len(traceback_text) + 10 > EmbedLimits.description:
        params["file"] = text_to_file(traceback_text, "traceback.py")
        embed.description = header

    else:
        embed.description = Markdown.codeblock(traceback_text, "py")
        embed.add_field(SPACE, header, inline=False)

    return params


async def error_handler(
    channel: Messageable,
    logger: logging.Logger,
    inter: CommandInteraction,
    exc: commands.CommandError,
) -> None:
    locale = inter.locale
    info = None
    error = exc

    if isinstance(exc, commands.NotOwner):
        info = i18n.get_message(locale, "cmd_dev")

    elif isinstance(exc, (commands.UserInputError, commands.CheckFailure)):
        info = str(exc)  # TODO: this isn't localized

    elif isinstance(exc, commands.MaxConcurrencyReached):
        if exc.number == 1 and exc.per is commands.BucketType.user:
            info = i18n.get_message(locale, "cmd_running")

        else:
            info = str(exc)

    elif isinstance(exc, commands.CommandInvokeError):
        error = exc.original
        if isinstance(error, TimeoutError):
            logger.warning("Command %s timed out", inter.application_command.qualified_name)
            info = i18n.get_message(locale, "cmd_timeout")

    if info is not None:
        with suppress(InteractionTimedOut):
            await inter.send(info, ephemeral=True)
        return

    params = exception_to_message(error, inter)

    if __debug__:
        logger.warning("Exception occured in %s", inter.application_command.qualified_name)
        user_params = params

    else:
        logger.exception("Unhandled exception:", exc_info=error)
        await channel.send(**params)
        user_params: SenderKeywords = {"content": i18n.get_message(locale, "cmd_error")}

    try:
        await inter.send(**user_params, ephemeral=not __debug__)

    except InteractionTimedOut:
        if __debug__:
            await channel.send(**params)


async def setup_channel_logger(client: Client, channel_id: int, logger: logging.Logger) -> None:
    """Creates an on_slash_command_error listener which sends tracebacks to selected channel."""
    assert isinstance(client, CommonBotBase)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        raise TypeError("Channel is not Messageable")

    client.add_listener(partial(error_handler, channel, logger), Event.slash_command_error)
