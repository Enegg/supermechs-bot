import logging
from contextlib import suppress

from app.disnake_types import Bot, CommandInteraction
from discord import EmbedLimits, markdown as md, text_to_file
from discord.interactions import inter_to_mention
from discord.message_builder import MessageBuilder
from disnake import Colour, Embed, Event, HTTPException, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands

from app import i18n, ui
from app.commands.cancellation import get_cancel_button_id
from app.core import CONFIG
from app.text_utils import Char
from app.utils import format_exception

_channel: Messageable | None = None
_LOG = logging.getLogger("event.command_error")


def cancel_button(inter: CommandInteraction, gettext: i18n.GetText) -> ui.ActionButton:
    return ui.ActionButton(
        custom_id=get_cancel_button_id(inter),
        style=ui.ButtonStyle.red,
        label=gettext("ui-cmd-cancel-button"),
        emoji="🛑",
    )


def get_user_error_message(
    inter: CommandInteraction, exc: commands.CommandError
) -> MessageBuilder | None:
    gettext = i18n.get_gettext(inter.locale)
    info = MessageBuilder()

    match exc:
        case commands.NotOwner():
            info.with_content(gettext("command-dev"))

        case commands.UserInputError() | commands.CheckFailure():
            # TODO: localize (some UserInputErrors are localized)
            info.with_content(str(exc))

        # 1 per user is special as it is cancellable
        case commands.MaxConcurrencyReached(number=1, per=commands.BucketType.user):
            info.with_content(gettext("command-running"))
            info.with_components(cancel_button(inter, gettext))

        case commands.MaxConcurrencyReached() as exc:
            # TODO: localize
            info.with_content(str(exc))

        case commands.CommandInvokeError(original=TimeoutError()):
            _LOG.warning("Command %s timed out", inter.application_command.qualified_name)
            info.with_content(gettext("command-timeout"))

        case _:
            info = None

    return info


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> MessageBuilder:
    arguments = ", ".join(f"`{option}: {value}`" for option, value in inter.filled_options.items())
    header = (
        f"Place: `{inter.guild or inter.channel}`\n"
        f"User: {inter.author.mention} (`{inter.author.display_name}`)\n"
        f"Command: {inter_to_mention(inter)} {arguments}"
    )
    embed = Embed(title="⚠️ Uncaught exception", color=Colour(0xFF0000))
    builder = MessageBuilder(embeds=[embed])
    traceback_text = format_exception(exc)

    if len(traceback_text) + 10 > EmbedLimits.description:
        builder.add_files(text_to_file(traceback_text, "traceback.py"))
        embed.description = f"{header}\nException: `{type(exc).__name__}: {exc}`"

    else:
        embed.description = md.codeblock(traceback_text, "py")
        embed.add_field(Char.BLANK, header, inline=False)

    return builder


async def on_slash_command_error(inter: CommandInteraction, exc: commands.CommandError) -> None:
    if (builder := get_user_error_message(inter, exc)) is not None:
        with suppress(InteractionTimedOut):
            await inter.send(**builder.get_send_params(), ephemeral=True)
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


def setup(bot: Bot) -> None:
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

    _channel = channel
