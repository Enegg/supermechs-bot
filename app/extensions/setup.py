from __future__ import annotations

import asyncio
import io
import traceback
import typing as t
from contextlib import redirect_stderr, redirect_stdout
from contextvars import ContextVar
from traceback import print_exception

from disnake import AllowedMentions, CommandInteraction, File, ModalInteraction, TextInputStyle
from disnake.ext import commands, plugins
from disnake.ui import TextInput

from config import TEST_GUILDS
from library_extensions import Markdown, ensure_file

if t.TYPE_CHECKING:
    from bot import SMBot

plugin = plugins.Plugin["SMBot"](slash_command_attrs={"guild_ids": TEST_GUILDS})
LAST_EXTENSION = ContextVar[str | None]("last_extension", default=None)


@plugin.slash_command()
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def ext(inter: CommandInteraction) -> None:
    pass


async def _ext_helper(
    inter: CommandInteraction, ext: str | None, func: t.Callable[[str], None]
) -> None:
    ext = ext or LAST_EXTENSION.get()

    if ext is None:
        return await inter.response.send_message("No extension cached.", ephemeral=True)

    try:
        func(ext)

    except commands.ExtensionError as error:
        with io.StringIO() as sio:
            sio.write("An error occured:\n```py\n")
            print_exception(type(error), error, error.__traceback__, file=sio)
            sio.write("```")
            await inter.send(sio.getvalue(), ephemeral=True)

    else:
        LAST_EXTENSION.set(ext)
        await inter.response.send_message("Success", ephemeral=True)


@ext.sub_command()
async def load(inter: CommandInteraction, ext: str | None = None) -> None:
    """Load an extension.

    Parameters
    ----------
    ext: The name of extension to perform action on.
    """
    await _ext_helper(inter, ext, plugin.bot.load_extension)


@ext.sub_command()
async def reload(inter: CommandInteraction, ext: str | None = None) -> None:
    """Reload an extension.

    Parameters
    ----------
    ext: The name of extension to perform action on.
    """
    await _ext_helper(inter, ext, plugin.bot.reload_extension)


@ext.sub_command()
async def unload(inter: CommandInteraction, ext: str | None = None) -> None:
    """Unload an extension.

    Parameters
    ----------
    ext: The name of extension to perform action on.
    """
    await _ext_helper(inter, ext, plugin.bot.unload_extension)


@load.autocomplete("ext")
@reload.autocomplete("ext")
@unload.autocomplete("ext")
async def ext_autocomplete(_: CommandInteraction, input: str) -> list[str]:
    input = input.lower()
    return [ext for ext in plugin.bot.extensions if input in ext.lower()]


@plugin.slash_command()
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def shutdown(inter: CommandInteraction) -> None:
    """Terminates the bot connection."""
    await inter.send("I will be back", ephemeral=True)
    await plugin.bot.close()


@plugin.slash_command(name="raise")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def force_error(
    inter: CommandInteraction,
    exception: str,
    arguments: str | None = None,
) -> None:
    """Explicitly raises provided exception.

    Parameters
    -----------
    exception: Name of the exception to raise.
    arguments: Optional arguments to pass to the exception.
    """
    err: type[commands.CommandError] | None = getattr(commands.errors, exception, None)

    if err is None or not issubclass(err, commands.CommandError):
        raise commands.UserInputError("Exception specified has not been found.")

    try:
        raise err(arguments)

    finally:
        await inter.send("Success", ephemeral=True)


@force_error.autocomplete("exception")
async def raise_autocomplete(_: CommandInteraction, input: str) -> list[str]:
    if len(input) < 2:
        return []

    input = input.lower()
    return [exc for exc in commands.errors.__all__ if input in exc.lower()][:25]


@plugin.slash_command(name="eval")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def eval_(inter: CommandInteraction | ModalInteraction, input: str | None = None) -> None:
    """Evaluates the given input as code.

    Parameters
    ----------
    input: code to execute.
    """
    if input is None:
        text_input = TextInput(
            label="Code to evaluate", custom_id="eval:input", style=TextInputStyle.multi_line
        )
        await inter.response.send_modal(
            title="Prompt", custom_id="eval:modal", components=text_input
        )

        def check(inter: ModalInteraction) -> bool:
            return inter.custom_id == "eval:modal"

        try:
            modal_inter: ModalInteraction = await plugin.bot.wait_for(
                "modal_submit", check=check, timeout=600
            )

        except asyncio.TimeoutError:
            return await inter.send("Modal timed out.", ephemeral=True)

        input = modal_inter.text_values[text_input.custom_id]
        inter = modal_inter

    input = Markdown.strip_codeblock(input)

    with io.StringIO() as local_stdout:
        with redirect_stdout(local_stdout), redirect_stderr(local_stdout):
            try:
                exec(input, globals() | {"bot": plugin.bot, "inter": inter})

            except Exception as ex:
                traceback.print_exception(type(ex), ex, ex.__traceback__, file=local_stdout)

        if local_stdout.tell() == 0:
            text = "No output."

        else:
            text = local_stdout.getvalue()

    line = "```\n{}```"

    if len(text) + len(line) - 2 <= 2000:
        await inter.send(
            line.format(text),
            allowed_mentions=AllowedMentions.none(),
            ephemeral=True,
        )

    else:
        file = File(ensure_file(text), "output.txt")
        await inter.send(file=file, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
