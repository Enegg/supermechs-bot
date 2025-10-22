import logging
from contextlib import suppress

from app.disnake_types import Bot, CommandInteraction
from discord import ComponentLimits, markdown as md, text_to_file
from discord.message_builder import MessageBuilder
from disnake import Colour, Event, HTTPException, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands

from app import i18n, ui
from app.core import CONFIG
from app.utils import format_exception

_channel: Messageable | None = None
_LOG = logging.getLogger("event.command_error")


def get_user_error_message(inter: CommandInteraction, exc: commands.CommandError) -> str | None:
    gettext = i18n.get_gettext(inter.locale)

    match exc:
        case commands.NotOwner():
            info = gettext("command-dev")

        case commands.UserInputError() | commands.CheckFailure():
            # TODO: localize (some UserInputErrors are localized)
            info = str(exc)

        case commands.MaxConcurrencyReached():
            # TODO: localize
            info = str(exc)

        case commands.CommandInvokeError(original=TimeoutError()):
            _LOG.warning("Command %s timed out", inter.application_command.qualified_name)
            info = gettext("command-timeout")

        case _:
            info = None

    return info


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> MessageBuilder:
    arguments = ", ".join(f"`{option}: {value}`" for option, value in inter.filled_options.items())
    components: list[ui.ContainerChildUIComponent] = []
    title_lines = [
        "## ⚠️ Uncaught exception",
        f"Place: <#{inter.channel_id}>",
        f"User: {inter.author.mention} (`{inter.author.display_name}`)",
        f"Command: {md.command_mention(inter)} {arguments}",
    ]

    traceback_text = format_exception(exc)
    builder = MessageBuilder()

    if len(traceback_text) + len("```\n```") <= ComponentLimits.text_display_content:
        components.append(ui.TextDisplay("\n".join(title_lines)))
        components.append(ui.TextDisplay(md.codeblock(traceback_text)))

    else:
        title_lines.append(f"Exception: `{type(exc).__name__}: {exc}`")
        components.append(ui.TextDisplay("\n".join(title_lines)))
        file = text_to_file(traceback_text, "traceback.py")
        builder.add_files(file)
        components.append(ui.file(file))

    container = ui.Container(*components, accent_colour=Colour(0xFF0000))
    return builder.with_components(container)


async def on_slash_command_error(inter: CommandInteraction, exc: commands.CommandError) -> None:
    if (msg := get_user_error_message(inter, exc)) is not None:
        with suppress(InteractionTimedOut):
            await inter.send(msg, ephemeral=True)
        return

    error = exc.original if isinstance(exc, commands.CommandInvokeError) else exc
    _LOG.error("Exception in %s", inter.application_command.qualified_name, exc_info=error)
    builder = exception_to_message(error, inter)
    await send_response(inter, builder)


if CONFIG.indev:

    async def send_response(inter: CommandInteraction, builder: MessageBuilder) -> None:
        params = builder.get_send_params()
        try:
            await inter.send(**params)

        except InteractionTimedOut:
            if _channel is not None:
                await _channel.send(**params)

else:

    async def send_response(inter: CommandInteraction, builder: MessageBuilder) -> None:
        if _channel is not None:
            await _channel.send(**builder.get_send_params())

        with suppress(InteractionTimedOut):
            await inter.send(i18n.get_message(inter.locale, "command-error"), ephemeral=True)


def setup(bot: Bot, /) -> None:
    bot.add_listener(on_slash_command_error, Event.slash_command_error)


async def setup_channel(bot: Bot, channel_id: int) -> None:
    global _channel
    try:
        channel = await bot.fetch_channel(channel_id)

    except HTTPException as exc:
        _LOG.error("Fetching logs channel failed", exc_info=exc)
        return

    if not isinstance(channel, Messageable):
        _LOG.error("Channel is not Messageable")
        return

    _LOG.info("Installed channel logger: #%s", channel.name)
    _channel = channel
