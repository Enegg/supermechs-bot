import logging
from contextlib import suppress

from app.disnake_types import CommandInteraction
from discord import EmbedLimits, markdown as md, text_to_file
from discord.messages import MessageTemplate
from disnake import Colour, Embed, Event, InteractionTimedOut
from disnake.abc import Messageable
from disnake.ext import commands

from app import i18n
from app.assets import INVISIBLE_CHAR
from app.bridges import ui
from app.commands.cancellation import make_id
from app.core import CONFIG
from app.plugins_factory import create_plugin
from app.utils import format_exception

plugin = create_plugin(__name__)
_channel: Messageable | None = None
_LOG = logging.getLogger("event.command_error")


if CONFIG.logs_channel_id is not None:
    # NOTE: the keyword is necessary to "save" the narrowed type of the id

    @plugin.load_hook()
    async def on_load(*, channel_id: int = CONFIG.logs_channel_id) -> None:
        global _channel
        await plugin.bot.wait_until_first_connect()
        channel = await plugin.bot.fetch_channel(channel_id)

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
    info = MessageTemplate()

    match exc:
        case commands.NotOwner():
            info.with_content(gettext("command-dev"))

        case commands.UserInputError() | commands.CheckFailure():
            # TODO: localize (some UserInputErrors are localized)
            info.with_content(str(exc))

        # 1 per user is special as it is cancellable
        case commands.MaxConcurrencyReached(number=1, per=commands.BucketType.user):
            (
                info.with_content(gettext("command-running")).with_components(
                    cancel_button(inter, gettext)
                )
            )

        case commands.MaxConcurrencyReached() as exc:
            # TODO: localize
            info.with_content(str(exc))

        case commands.CommandInvokeError(original=TimeoutError()):
            _LOG.warning("Command %s timed out", inter.application_command.qualified_name)
            info.with_content(gettext("command-timeout"))

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
        template = template.add_files(text_to_file(traceback_text, "traceback.py"))
        embed.description = header

    else:
        embed.description = md.codeblock(traceback_text, "py")
        embed.add_field(INVISIBLE_CHAR, header, inline=False)

    return template


@plugin.listener(Event.slash_command_error)
async def on_slash_command_error(inter: CommandInteraction, exc: commands.CommandError) -> None:
    if (template := get_user_error_message(inter, exc)) is not None:
        with suppress(InteractionTimedOut):
            await inter.send(**template.get_send_params(), ephemeral=True)
        return

    error = exc.original if isinstance(exc, commands.CommandInvokeError) else exc
    _LOG.exception("Exception in %s", inter.application_command.qualified_name, exc_info=error)
    template = exception_to_message(error, inter)

    if CONFIG.indev:
        try:
            await inter.send(**template.get_send_params())

        except InteractionTimedOut:
            if _channel is not None:
                await _channel.send(**template.get_send_params())

    else:
        if _channel is not None:
            await _channel.send(**template.get_send_params())

        with suppress(InteractionTimedOut):
            await inter.send(i18n.get_message(inter.locale, "command-error"), ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
