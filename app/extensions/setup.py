import io
import traceback
import typing as t

from disnake import CommandInteraction
from disnake.ext import commands, plugins

from config import TEST_GUILDS
from discord_extensions import OPTION_LIMIT

exception_names: t.Final = commands.errors.__all__

plugin: t.Final = plugins.Plugin[commands.InteractionBot](
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


setup, teardown = plugin.create_extension_handlers()
