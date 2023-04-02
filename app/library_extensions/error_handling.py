import io
import logging
import traceback
from functools import partial

from disnake import Client, CommandInteraction, File, LocalizationProtocol
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.utils import MISSING

from .text_formatting import localized_text

__all__ = ("setup_channel_logger",)


def exception_to_message(text: str, exception: Exception) -> tuple[str, File]:
    lines = traceback.format_exception(exception)
    total_length = sum(map(len, lines))
    traceback_text = "".join(lines)

    if len(text) + total_length + 10 > 2000:
        bio = io.BytesIO(traceback_text.encode())
        file = File(bio, "traceback.py")

    else:
        file = MISSING
        text = (
            f"{text}\n"
            "```py\n"
            f"{traceback_text}```"
        )

    return text, file


async def on_slash_command_error(
    channel: Messageable,
    i18n: LocalizationProtocol,
    logger: logging.Logger,
    /,
    inter: CommandInteraction,
    error: commands.CommandError,
) -> None:
    if isinstance(error, commands.NotOwner):
        info = localized_text("This is a developer-only command.", "CMD_DEV", i18n, inter.locale)

    elif isinstance(error, (commands.UserInputError, commands.CheckFailure)):
        info = str(error)

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

        text = (
            f"{error}\n"
            f"Place: `{inter.guild or inter.channel}`\n"
            f"Command invocation: {inter.author.mention} ({inter.author.display_name})"
            f" `/{inter.application_command.qualified_name}` {arguments}"
        )

        if __debug__:
            info = text

        else:
            message_text, file = exception_to_message(text, error)
            await channel.send(message_text, file=file)
            logger.exception(text, exc_info=error)

            info = localized_text(
                "Command executed with an error...", "CMD_ERROR", i18n, inter.locale
            )

    await inter.send(info, ephemeral=True)


async def setup_channel_logger(client: Client, channel_id: int, logger: logging.Logger) -> None:
    """"""
    assert isinstance(client, commands.BotBase)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        raise TypeError("Channel is not Messageable")

    client.add_listener(
        partial(on_slash_command_error, channel, client.i18n, logger), "on_slash_command_error"
    )
