import typing
from collections import abc

from disnake import CommandInteraction
from disnake.ext import commands, plugins

from config import TEST_GUILDS
from discord_extensions import AutocompleteReturnType, InteractionLimits
from shared.utils import format_exception

exception_names: typing.Final = commands.errors.__all__

plugin: typing.Final = plugins.Plugin[commands.InteractionBot](
    name="Setup", slash_command_attrs={"guild_ids": TEST_GUILDS}, logger=__name__
)
last_extension: str | None = None


@plugin.slash_command(name="plugin")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def plugin_(inter: CommandInteraction) -> None:
    del inter


async def _ext_helper(
    inter: CommandInteraction, plugin: str | None, func: abc.Callable[[str], None]
) -> None:
    global last_extension
    plugin = plugin or last_extension

    if plugin is None:
        return await inter.response.send_message("No extension cached.", ephemeral=True)

    try:
        func(plugin)

    except commands.ExtensionError as exc:
        traceback_text = f"An exception occurred:\n```py\n{format_exception(exc)}```"
        await inter.response.send_message(traceback_text, ephemeral=True)

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
) -> typing.NoReturn:
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
def get_matching_exceptions(_: CommandInteraction, input: str) -> AutocompleteReturnType:
    if len(input) < 2:
        return []

    input = input.lower()
    matching = [exc for exc in exception_names if input in exc.lower()]
    del matching[InteractionLimits.autocomplete_options :]
    return matching


setup, teardown = plugin.create_extension_handlers()
