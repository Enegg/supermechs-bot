import logging
from contextlib import suppress
from functools import partial

from app import i18n
from app.shared.utils import SPACE, format_exception
from discord_plus import EmbedLimits, ListenerRegistry, Markdown, SenderKeywords, text_to_file

from disnake import Client, Colour, CommandInteraction, Embed, Event, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands

__all__ = ("setup_channel_logger",)

_LOGGER = logging.getLogger("event.command_error")


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
    traceback_text = format_exception(exc)

    if len(traceback_text) + 10 > EmbedLimits.description:
        params["file"] = text_to_file(traceback_text, "traceback.py")
        embed.description = header

    else:
        embed.description = Markdown.codeblock(traceback_text, "py")
        embed.add_field(SPACE, header, inline=False)

    return params


async def handle_user_exception(inter: CommandInteraction, exc: commands.CommandError) -> bool:
    gettext = i18n.get_gettext(inter.locale)

    if isinstance(exc, commands.NotOwner):
        info = gettext("command-dev")

    elif isinstance(exc, commands.UserInputError | commands.CheckFailure):
        info = str(exc)  # TODO: localize (some UserInputErrors are localized)

    elif isinstance(exc, commands.MaxConcurrencyReached):
        if exc.number == 1 and exc.per is commands.BucketType.user:
            info = gettext("command-running")

        else:
            info = str(exc)  # TODO: localize

    elif isinstance(exc, commands.CommandInvokeError) and isinstance(exc.original, TimeoutError):
        _LOGGER.warning("Command %s timed out", inter.application_command.qualified_name)
        info = gettext("command-timeout")

    else:
        return False

    with suppress(InteractionTimedOut):
        await inter.send(info, ephemeral=True)

    return True


async def handle_dev_error(
    inter: CommandInteraction, exc: Exception, channel: Messageable
) -> None:
    _LOGGER.warning("Exception occurred in %s", inter.application_command.qualified_name)
    log_params = exception_to_message(exc, inter)

    try:
        await inter.send(**log_params)

    except InteractionTimedOut:
        await channel.send(**log_params)


async def handle_prod_error(
    inter: CommandInteraction, exc: Exception, channel: Messageable
) -> None:
    _LOGGER.exception("Unhandled exception:", exc_info=exc)
    await channel.send(**exception_to_message(exc, inter))

    with suppress(InteractionTimedOut):
        await inter.send(i18n.get_message(inter.locale, "command-error"), ephemeral=True)


async def exception_handler(
    channel: Messageable, inter: CommandInteraction, exc: commands.CommandError
) -> None:
    if await handle_user_exception(inter, exc):
        return

    error = exc.original if isinstance(exc, commands.CommandInvokeError) else exc

    if __debug__:
        await handle_dev_error(inter, error, channel)

    else:
        await handle_prod_error(inter, error, channel)


async def setup_channel_logger(client: Client, channel_id: int) -> None:
    """Creates an `on_slash_command_error` listener which sends tracebacks to selected channel."""
    assert isinstance(client, ListenerRegistry)
    channel = await client.fetch_channel(channel_id)

    if not isinstance(channel, Messageable):
        msg = "Channel is not Messageable"
        raise TypeError(msg)

    client.add_listener(partial(exception_handler, channel), Event.slash_command_error)
