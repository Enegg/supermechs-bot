import ast
import inspect
import io
import linecache
import time
import types
from collections import abc
from contextlib import redirect_stderr, redirect_stdout

import anyio

from app.disnake_types import CommandInteraction, Interaction, ModalInteraction, Plugin
from discord import MessageLimits, markdown as md, text_to_file
from discord.ui import random_str, wait_for_components
from disnake.ext import commands

from app.bridges import ui
from app.core import CONFIG
from app.utils import format_exception

plugin = Plugin(name="Code-eval", logger="ext")
MODAL_SUFFIX = "code"
WAIT_EMOJI = "<a:wait:731884722166431754>"
CANCEL_DELAY = 3


async def runner(cs: anyio.CancelScope, fn: abc.Callable[[], object], sio: io.StringIO) -> None:
    # NOTE: .run_sync somehow screws up imports/globals
    # TODO: a way to run code in isolation?
    # right now, any expensive code /will/ affect the entire bot
    # otoh, full isolation will likely require a second event loop
    # which can cause issues
    with redirect_stdout(sio), redirect_stderr(sio):
        try:
            obj = fn()

            if inspect.isawaitable(obj):
                await obj

        except Exception as exc:
            sio.write(format_exception(exc))

    cs.cancel()

async def waiter(cs: anyio.CancelScope, inter: Interaction, cancelled: anyio.Event) -> None:
    await anyio.sleep(CANCEL_DELAY)

    button = ui.ActionButton(label="Cancel", style=ui.ButtonStyle.red)
    await inter.edit_original_response(f"{WAIT_EMOJI} Processing...", components=[button])
    button_inter, _ = await wait_for_components(button, client=plugin.bot, user_id=inter.author.id)
    cancelled.set()
    with anyio.CancelScope(shield=True):
        # this is the only place we acknowledge the interaction, so shield it
        await button_inter.response.defer()
    cs.cancel()

async def eval_code(inter: Interaction, code: str) -> None:
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
        cancelled = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(runner, tg.cancel_scope, fn, sio)
            tg.start_soon(waiter, tg.cancel_scope, inter, cancelled)

        run_time = time.perf_counter() - start_time

        output = sio.getvalue() or "[No output]"
        status = f"{'cancelled after' if cancelled.is_set() else 'finished in'} {run_time:.2f}s"

    title = f"-# Code {status}"

    # 2 newlines + 6 backticks
    if len(output) + len(title) + 8 <= MessageLimits.content:
        await inter.edit_original_response(f"{title}\n{md.codeblock(output)}", components=None)

    else:
        file = text_to_file(output, "output.txt")
        await inter.edit_original_response(title, file=file, components=None)


@plugin.slash_command(name="eval", guild_ids=CONFIG.test_guild_ids)
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def eval_(inter: CommandInteraction, code: str | None = None) -> None:
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
        label="Code to evaluate", custom_id=MODAL_SUFFIX, style=ui.TextInputStyle.paragraph
    )
    await inter.response.send_modal(
        title="Prompt", custom_id=f"{random_str()}:{MODAL_SUFFIX}", components=text_input
    )


@plugin.listener()
async def on_modal_submit(inter: ModalInteraction, /) -> None:
    if not inter.custom_id.endswith(MODAL_SUFFIX):
        return

    code = inter.text_values[MODAL_SUFFIX]
    await eval_code(inter, code)


setup, teardown = plugin.create_extension_handlers()
