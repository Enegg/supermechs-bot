import io
import logging
import traceback
from functools import partial

from disnake import Client, CommandInteraction, File, LocalizationProtocol
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.ext.commands.common_bot_base import CommonBotBase
from disnake.utils import MISSING

from .text_formatting import Markdown, localized_text

__all__ = ("setup_channel_logger",)


def exception_to_message(content: str, exception: BaseException) -> tuple[str, File]:
    """Formats exception data and returns message content & file to send a message with.

    Formatted traceback is wrapped in a codeblock and appended to content if the resulting string
    stays under 2000 character limit, otherwise creates a File and returns content unaffected.
    """
    traceback_text = "".join(traceback.format_exception(exception))

    if len(content) + len(traceback_text) + 10 > 2000:
        bio = io.BytesIO(traceback_text.encode())
        file = File(bio, "traceback.py")

    else:
        file = MISSING
        content = f"{content}\n{Markdown.codeblock(traceback_text), 'py'}"

    return content, file


async def on_slash_command_error(
    channel: Messageable,
    i18n: LocalizationProtocol,
    logger: logging.Logger,
    /,
    inter: CommandInteraction,
    error: commands.CommandError,
) -> None:
    file = MISSING

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

        text = (
            f"{error}\n"
            f"Place: `{inter.guild or inter.channel}`\n"
            f"Command invocation: {inter.author.mention} ({inter.author.display_name}) "
            f"`/{inter.application_command.qualified_name}` {arguments}"
        )
        message_content, file = exception_to_message(text, error)

        if __debug__:
            info = message_content

        else:
            await channel.send(message_content, file=file)
            logger.exception(text, exc_info=error)

            info = localized_text(
                "Command executed with an error...", "CMD_ERROR", i18n, inter.locale
            )

    await inter.send(info, file=file, ephemeral=True)


async def setup_channel_logger(client: Client, channel_id: int, logger: logging.Logger) -> None:
    """Creates an on_slash_command_error listener which sends tracebacks to selected channel."""
    assert isinstance(client, CommonBotBase)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        raise TypeError("Channel is not Messageable")

    client.add_listener(
        partial(on_slash_command_error, channel, client.i18n, logger), "on_slash_command_error"
    )
