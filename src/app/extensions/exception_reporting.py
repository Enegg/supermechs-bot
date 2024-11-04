import logging
from contextlib import suppress

from discord import EmbedLimits, markdown as md, text_to_file
from discord.interactions import MessageTemplate
from disnake import Colour, CommandInteraction, Embed, Event, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.utils import MISSING
from disnake_plugins import Plugin

from app import i18n
from app.assets import INVISIBLE_CHAR
from app.bridges import ui
from app.bridges.cancellation import make_id
from app.core import ENV
from app.utils import format_exception

plugin = Plugin[commands.InteractionBot](name="Exception-logs", logger="ext")
_channel: Messageable = MISSING
_LOG = logging.getLogger("event.command_error")


@plugin.load_hook()
async def on_load() -> None:
    global _channel  # noqa: PLW0603
    await plugin.bot.wait_until_first_connect()
    channel = await plugin.bot.fetch_channel(ENV.logs_channel_id)

    if not isinstance(channel, Messageable):
        msg = "Channel is not Messageable"
        raise TypeError(msg)

    _channel = channel


def cancel_button(inter: CommandInteraction, gettext: i18n.GetText) -> ui.ActionButton:
    return ui.ActionButton(
        custom_id=make_id(inter),
        style=ui.ButtonStyle.red,
        label=gettext("ui-cmd-cancel-button"),
        emoji="🛑",
    )


def get_user_error_message(
    inter: CommandInteraction, exc: commands.CommandError
) -> MessageTemplate | None:
    gettext = i18n.get_gettext(inter.locale)

    match exc:
        case commands.NotOwner():
            info = MessageTemplate(gettext("command-dev"))

        case commands.UserInputError() | commands.CheckFailure():
            # TODO: localize (some UserInputErrors are localized)
            info = MessageTemplate(str(exc))

        case commands.MaxConcurrencyReached(number=1, per=commands.BucketType.user):
            info = MessageTemplate(
                gettext("command-running"),
                components=cancel_button(inter, gettext),
            )

        case commands.MaxConcurrencyReached() as exc:
            # TODO: localize
            info = MessageTemplate(str(exc))

        case commands.CommandInvokeError(original=TimeoutError()):
            _LOG.warning("Command %s timed out", inter.application_command.qualified_name)
            info = MessageTemplate(gettext("command-timeout"))

        case _:
            info = None

    return info


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> MessageTemplate:
    arguments = ", ".join(f"`{option}: {value}`" for option, value in inter.filled_options.items())
    header = (
        f"Place: `{inter.guild or inter.channel}`\n"
        f"User: {inter.author.mention} (`{inter.author.display_name}`)\n"
        f"Command: `/{inter.application_command.qualified_name}` {arguments}\n"
        f"Exception: `{type(exc).__name__}: {exc}`"
    )
    embed = Embed(title="⚠️ Uncaught exception", color=Colour(0xFF0000))
    template = MessageTemplate(embeds=[embed])
    traceback_text = format_exception(exc)

    if len(traceback_text) + 10 > EmbedLimits.description:
        template = template.with_files(text_to_file(traceback_text, "traceback.py"))
        embed.description = header

    else:
        embed.description = md.codeblock(traceback_text, "py")
        embed.add_field(INVISIBLE_CHAR, header, inline=False)

    return template


@plugin.listener(Event.slash_command_error)
async def on_slash_command_error(inter: CommandInteraction, exc: commands.CommandError) -> None:
    if (msg := get_user_error_message(inter, exc)) is not None:
        with suppress(InteractionTimedOut):
            await msg.ephemeral().send_any_response(inter)
        return

    error = exc.original if isinstance(exc, commands.CommandInvokeError) else exc
    _LOG.exception("Exception in %s", inter.application_command.qualified_name, exc_info=error)
    template = exception_to_message(error, inter)

    if __debug__:
        try:
            await template.send_any_response(inter)

        except InteractionTimedOut:
            await template.send_to_channel(_channel)

    else:
        await template.send_to_channel(_channel)

        with suppress(InteractionTimedOut):
            await inter.send(i18n.get_message(inter.locale, "command-error"), ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
