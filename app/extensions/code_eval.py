import ast
import inspect
import io
import linecache
import traceback
import types
import typing as t
from contextlib import redirect_stderr, redirect_stdout

import anyio
from disnake import CommandInteraction, TextInputStyle
from disnake.ext import commands, plugins
from disnake.ui import TextInput

import config
from discord_extensions import Markdown, MessageLimits, text_to_file
from discord_extensions.ui import random_str, wait_for_modal

plugin: t.Final = plugins.Plugin[commands.InteractionBot](name="Code-eval", logger=__name__)


@plugin.slash_command(name="eval", guild_ids=config.TEST_GUILDS)
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def eval_(inter: CommandInteraction, code: str | None = None) -> None:
    """Evaluates the given input as code.

    Parameters
    ----------
    code: code to execute.
    """
    last_inter = inter

    if code is None:
        custom_id = random_str()
        text_input = TextInput(
            label="Code to evaluate", custom_id="code", style=TextInputStyle.paragraph
        )
        await inter.response.send_modal(title="Prompt", custom_id=custom_id, components=text_input)

        try:
            last_inter = await wait_for_modal(plugin.bot, custom_id)

        except TimeoutError:
            return await inter.send("Modal timed out.", ephemeral=True)

        code = last_inter.text_values[text_input.custom_id]
        del custom_id, text_input

    compiled_code: types.CodeType = compile(
        source=Markdown.strip_codeblock(code),
        filename="<eval command>",
        mode="exec",
        flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
    )
    # exception printing purposes
    linecache.cache[compiled_code.co_filename] = (
        len(code),
        None,
        code.splitlines(keepends=True),
        compiled_code.co_filename
    )
    del inter, code
    sio = io.StringIO()

    with redirect_stdout(sio), redirect_stderr(sio):
        # TODO: run in thread
        fn = types.FunctionType(compiled_code, {"bot": plugin.bot, "inter": last_inter})
        try:
            obj = fn()
            if inspect.isawaitable(obj):
                with anyio.fail_after(config.RESPONSE_TIME_LIMIT):
                    await obj
            del obj

        except TimeoutError:
            sio.write("Command execution timed out")

        except Exception as exc:
            traceback.print_exception(exc, file=sio)

        del compiled_code

    text = sio.getvalue()
    del sio

    if len(text) == 0:
        if last_inter.response.is_done():
            # response happened during exec
            return
        text = "No output."

    # newline and 6 backticks
    if len(text) + 7 <= MessageLimits.content:
        await last_inter.send(f"```\n{text}```", ephemeral=True)

    else:
        file = text_to_file(text, "output.txt")
        await last_inter.send(file=file, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
