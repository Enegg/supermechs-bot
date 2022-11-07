from __future__ import annotations

import io
import typing as t
from contextvars import ContextVar
from traceback import print_exception

from disnake import AllowedMentions, CommandInteraction
from disnake.ext import commands, plugins

from app.config import TEST_GUILDS
from app.library_extensions import str_to_file

if t.TYPE_CHECKING:
    from app.bot import SMBot

plugin = plugins.Plugin["SMBot"].with_metadata(slash_command_attrs={"guild_ids": TEST_GUILDS})
LAST_EXTENSION = ContextVar[str | None]("last_extension", default=None)


@plugin.slash_command()
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def ext(
    inter: CommandInteraction,
    ext: str | None = None,
    action: t.Literal["load", "reload", "unload"] = "reload",
) -> None:
    """Extension manager.

    Parameters
    -----------
    action: The type of action to perform.
    ext: The name of extension to perform action on.
    """
    ext = ext or LAST_EXTENSION.get()

    if ext is None:
        return await inter.response.send_message("No extension cached.", ephemeral=True)

    funcs = dict(
        load=plugin.bot.load_extension,
        reload=plugin.bot.reload_extension,
        unload=plugin.bot.unload_extension,
    )

    try:
        funcs[action](ext)

    except commands.ExtensionError as error:
        with io.StringIO() as sio:
            sio.write("An error occured:\n```py\n")
            print_exception(type(error), error, error.__traceback__, file=sio)
            sio.write("```")
            await inter.send(sio.getvalue(), ephemeral=True)

    else:
        await inter.response.send_message("Success", ephemeral=True)
        LAST_EXTENSION.set(ext)


@ext.autocomplete("ext")
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
async def eval_(inter: CommandInteraction, input: str) -> None:
    """Evaluates the given input as code.

    Parameters
    ----------
    input: code to execute.
    """
    input = input.strip()

    out = io.StringIO()

    def print_(*args: t.Any, **kwargs: t.Any) -> None:
        print(*args, **kwargs, file=out)

    output = eval(input, globals() | {"bot": plugin.bot, "inter": inter, "print": print_})
    std = out.getvalue()

    if output is None or not std:
        msg = f"```\n{std or output}```"

    else:
        msg = f"```\n{output}```\n**stdout:**\n```\n{std}```"

    if len(msg) > 2000:
        file = str_to_file(msg.strip("` "))
        await inter.send(file=file, ephemeral=True)

    else:
        await inter.send(
            msg,
            allowed_mentions=AllowedMentions.none(),
            ephemeral=True,
        )


setup, teardown = plugin.create_extension_handlers()
