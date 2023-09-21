from __future__ import annotations

import ast
import io
import traceback
import typing as t
from contextlib import redirect_stderr, redirect_stdout

from disnake import CommandInteraction, File, TextInputStyle
from disnake.ext import commands, plugins
from disnake.ui import TextInput

from config import TEST_GUILDS
from library_extensions import MSG_CHAR_LIMIT, OPTION_LIMIT, Markdown
from library_extensions.ui import wait_for_modal

exception_names: t.Final = commands.errors.__all__

plugin: t.Final = plugins.Plugin["commands.InteractionBot"](
    name="Setup", slash_command_attrs={"guild_ids": TEST_GUILDS}, logger=__name__
)
last_extension: str | None = None


@plugin.slash_command(name="plugin")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def plugin_(inter: CommandInteraction) -> None:
    del inter


async def _ext_helper(
    inter: CommandInteraction, plugin: str | None, func: t.Callable[[str], None]
) -> None:
    global last_extension
    plugin = plugin or last_extension

    if plugin is None:
        return await inter.response.send_message("No extension cached.", ephemeral=True)

    try:
        func(plugin)

    except commands.ExtensionError as error:
        sio = io.StringIO("An error occured:\n```py\n")
        traceback.print_exception(error, file=sio)
        sio.write("```")
        await inter.response.send_message(sio.getvalue(), ephemeral=True)

    else:
        last_extension = plugin
        await inter.response.send_message("Success", ephemeral=True)


@plugin_.sub_command()
async def load(inter: CommandInteraction, ext: str | None = None) -> None:
    """Load an extension.

    Parameters
    ----------
    ext: The name of extension to perform action on.
    """
    await _ext_helper(inter, ext, plugin.bot.load_extension)


@plugin_.sub_command()
async def reload(inter: CommandInteraction, ext: str | None = None) -> None:
    """Reload an extension.

    Parameters
    ----------
    ext: The name of extension to perform action on.
    """
    await _ext_helper(inter, ext, plugin.bot.reload_extension)


@plugin_.sub_command()
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
async def plugin_name_autocomplete(_: CommandInteraction, input: str) -> list[str]:
    input = input.lower()
    return [ext for ext in plugin.bot.extensions if input in ext.lower()]


@plugin.slash_command()
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def shutdown(inter: CommandInteraction) -> None:
    """Terminates the bot connection."""
    await inter.response.send_message("I will be back", ephemeral=True)
    plugin.logger.warning("Bot shutdown initiated")
    await plugin.bot.close()


@plugin.slash_command(name="raise")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def force_error(
    inter: CommandInteraction,
    exception: str,
    message: str = "Exception raised via /raise",
) -> t.NoReturn:
    """Explicitly raises chosen exception.

    Parameters
    ----------
    exception: Name of the exception to raise.
    message: Optional message to pass to the exception.
    """
    if exception not in exception_names:
        raise commands.UserInputError("Unknown exception.")

    exc: type[commands.CommandError] = getattr(commands.errors, exception)
    await inter.response.defer()
    raise exc(message)


@force_error.autocomplete("exception")
async def raise_autocomplete(_: CommandInteraction, input: str) -> list[str]:
    if len(input) < 2:
        return []

    input = input.lower()
    matching = [exc for exc in exception_names if input in exc.lower()]
    del matching[OPTION_LIMIT:]
    return matching


@plugin.slash_command(name="eval")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def eval_(inter: CommandInteraction, code: str | None = None) -> None:
    """Evaluates the given input as code.

    Parameters
    ----------
    code: code to execute.
    """
    response_inter = inter

    if code is None:
        text_input = TextInput(
            label="Code to evaluate", custom_id="eval:input", style=TextInputStyle.paragraph
        )
        await inter.response.send_modal(
            title="Prompt", custom_id="eval:modal", components=text_input
        )

        try:
            response_inter = await wait_for_modal(plugin.bot, "eval:modal")

        except TimeoutError:
            return await inter.send("Modal timed out.", ephemeral=True)

        code = response_inter.text_values[text_input.custom_id]

    code = Markdown.strip_codeblock(code)
    local_stdout = io.StringIO()

    compiled_code = compile(
        code,
        filename="<eval command>",
        mode="exec",
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    )

    with redirect_stdout(local_stdout), redirect_stderr(local_stdout):
        try:
            exec(
                compiled_code,
                {},  # passing globals() would allow for uncontrolled mutation of them
                {"bot": plugin.bot, "inter": response_inter}
            )
        except Exception as exc:
            traceback.print_exception(exc, file=local_stdout)

    if len(text := local_stdout.getvalue()) == 0:
        # response happened during exec
        if response_inter.response.is_done():
            return
        text = "No output."

    # newline and 6 backticks
    if len(text) + 7 <= MSG_CHAR_LIMIT:
        await response_inter.send(f"```\n{text}```", ephemeral=True)

    else:
        file = File(io.BytesIO(text.encode()), "output.txt")
        await response_inter.send(file=file, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
