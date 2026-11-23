from contextlib import suppress

from discord import ComponentLimits, markdown as md, text_to_file
from discord.message_builder import MessageBuilder
from disnake import InteractionTimedOut

from app import i18n, ui
from app.assets import Colors
from app.core.config import CONFIG
from app.core.state import State
from app.typeshed import CommandInteraction
from app.utils import format_exception


def exception_to_message(exc: BaseException, inter: CommandInteraction, /) -> MessageBuilder:
    arguments = ", ".join(f"`{option}: {value}`" for option, value in inter.filled_options.items())
    container, add_component = ui.container(accent_color=Colors.error)
    title_lines = [
        "## ⚠️ Uncaught exception",
        f"Place: {md.channel_mention(inter.channel_id)}",
        f"User: {inter.author.mention} (`{inter.author.display_name}`)",
        f"Command: {md.command_mention(inter)} {arguments}",
    ]

    traceback_text = format_exception(exc)
    builder = MessageBuilder()

    if md.codeblock_size(traceback_text) <= ComponentLimits.text_display_content:
        add_component(ui.TextDisplay("\n".join(title_lines)))
        add_component(ui.TextDisplay(md.codeblock(traceback_text)))

    else:
        title_lines.append(f"Exception: `{type(exc).__name__}: {exc}`")
        add_component(ui.TextDisplay("\n".join(title_lines)))
        file = text_to_file(traceback_text, "traceback.py")
        builder.add_files(file)
        add_component(ui.file(file))

    return builder.with_components(container)


if CONFIG.indev:

    async def send_response(
        inter: CommandInteraction, builder: MessageBuilder, state: State
    ) -> None:
        params = builder.get_send_params()
        try:
            await inter.send(**params)

        except InteractionTimedOut:
            if state.logs_channel is not None:
                await state.logs_channel.send(**params)

else:

    async def send_response(
        inter: CommandInteraction, builder: MessageBuilder, state: State
    ) -> None:
        if state.logs_channel is not None:
            await state.logs_channel.send(**builder.get_send_params())

        with suppress(InteractionTimedOut):
            await inter.send(
                i18n.get_message(state.i18n, inter.locale, "command-error"), ephemeral=True
            )
