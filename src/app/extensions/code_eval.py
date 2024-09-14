import ast
import inspect
import io
import linecache
import time
import types
from collections import abc
from contextlib import redirect_stderr, redirect_stdout
from typing import Final

import anyio

import disnake
from discord import MessageLimits, markdown as md, text_to_file
from discord.ui import random_str, wait_for_components
from disnake import TextInputStyle, ui
from disnake.ext import commands, plugins

from app.bridges import format_exception
from app.bridges.ui import ActionButton
from app.core import ENV

plugin: Final = plugins.Plugin[commands.InteractionBot](name="Code-eval", logger=__name__)
MODAL_SUFFIX = "code"
WAIT_EMOJI = "<a:wait:731884722166431754>"
CANCEL_DELAY = 3


async def runner(fn: abc.Callable[[], object], sio: io.StringIO, cs: anyio.CancelScope) -> None:
    # NOTE: .run_sync somehow screws up imports/globals
    # TODO: a way to run code in isolation?
    # right now, any expensive code /will/ affect the entire bot
    # otoh, full isolation will likely require a second event loop
    # which can cause issues
    try:
        obj = fn()

        if inspect.isawaitable(obj):
            await obj

    except Exception as exc:
        sio.write(format_exception(exc))

    cs.cancel()


async def eval_code(inter: disnake.Interaction, code: str) -> None:
    await inter.response.defer(with_message=True, ephemeral=True)

    start_time = time.perf_counter()
    code = md.strip_codeblock(code)
    filename = "<eval command>"

    # 3.11 traceback enhancements pull from linecache
    linecache.cache[filename] = (
        len(code),
        time.time(),
        code.splitlines(keepends=True),
        filename,
    )
    try:
        compiled_code: types.CodeType = compile(
            source=code,
            filename=filename,
            mode="exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        )
    except SyntaxError as exc:
        output = format_exception(exc)
        status = "failed to compile"

    else:
        context = {"bot": plugin.bot, "inter": inter, "sleep": anyio.sleep}
        fn = types.FunctionType(compiled_code, context, name="fn")

        sio = io.StringIO()
        cancelled: bool = False

        async def waiter(inter: disnake.Interaction, cs: anyio.CancelScope) -> None:
            nonlocal cancelled
            await anyio.sleep(CANCEL_DELAY)

            button = ActionButton(label="Cancel", style=disnake.ButtonStyle.red)
            await inter.edit_original_response(f"{WAIT_EMOJI} Processing...", components=[button])
            button_inter, _ = await wait_for_components(
                button, client=plugin.bot, user_id=inter.author.id
            )
            cancelled = True
            with anyio.CancelScope(shield=True):
                # this is the only place we acknowledge the interaction, so shield it
                await button_inter.response.defer()
            cs.cancel()

        with redirect_stdout(sio), redirect_stderr(sio):
            async with anyio.create_task_group() as tg:
                tg.start_soon(runner, fn, sio, tg.cancel_scope)
                tg.start_soon(waiter, inter, tg.cancel_scope)

            run_time = time.perf_counter() - start_time

        output = sio.getvalue() or "[No output]"
        status = (
            f"cancelled after {run_time:.2f}s" if cancelled else f"finished in {run_time:.2f}s"
        )

    title = f"-# Code {status}"

    # 2 newlines + 6 backticks
    if len(output) + len(title) + 8 <= MessageLimits.content:
        await inter.edit_original_response(f"{title}\n{md.codeblock(output)}", components=None)

    else:
        file = text_to_file(output, "output.txt")
        await inter.edit_original_response(title, file=file, components=None)


@plugin.slash_command(name="eval", guild_ids=ENV.test_guild_ids)
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def eval_(inter: disnake.CommandInteraction, code: str | None = None) -> None:
    """Evaluate the given input as code.

    Parameters
    ----------
    code:
        code to execute.
    """
    if code is not None:
        await eval_code(inter, code)
        return

    text_input = ui.TextInput(
        label="Code to evaluate", custom_id=MODAL_SUFFIX, style=TextInputStyle.paragraph
    )
    await inter.response.send_modal(
        title="Prompt", custom_id=f"{random_str()}:{MODAL_SUFFIX}", components=text_input
    )


@plugin.listener()
async def on_modal_submit(inter: disnake.ModalInteraction, /) -> None:
    if not inter.custom_id.endswith(MODAL_SUFFIX):
        return

    code = inter.text_values[MODAL_SUFFIX]
    await eval_code(inter, code)


setup, teardown = plugin.create_extension_handlers()
