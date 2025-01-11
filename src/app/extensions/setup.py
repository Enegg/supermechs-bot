from collections import abc
from typing import NoReturn

import disnake
from app.disnake_types import CommandInteraction
from discord import AutocompleteReturnType, InteractionLimits
from discord.extensions import walk_extensions
from disnake.ext import commands

from app import i18n
from app.core import CONFIG
from app.plugins_factory import create_plugin
from app.utils import format_exception

plugin = create_plugin(__name__, slash_command_attrs={"guild_ids": CONFIG.test_guild_ids})
KNOWN_EXCEPTION_NAMES = tuple(commands.errors.__all__)
KNOWN_PLUGIN_PATHS = tuple(walk_extensions("extensions"))
# TODO: CommandLimits.param_options or whatever
assert len(KNOWN_PLUGIN_PATHS) <= InteractionLimits.autocomplete_options

recently_loaded_plugin: str | None = None


@plugin.slash_command(name="plugin")
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def plugin_(inter: CommandInteraction) -> None:
    del inter


async def _plugin_helper(
    inter: CommandInteraction, plugin: str | None, func: abc.Callable[[str], None], action: str
) -> None:
    global recently_loaded_plugin  # noqa: PLW0603
    plugin = plugin or recently_loaded_plugin

    if plugin is None:
        return await inter.response.send_message("No extension cached.", ephemeral=True)

    try:
        func(plugin)

    except commands.ExtensionError as exc:
        traceback_text = f"An exception occurred:\n```py\n{format_exception(exc)}```"
        await inter.response.send_message(traceback_text, ephemeral=True)

    else:
        recently_loaded_plugin = plugin
        await inter.response.send_message(f"{action.title()}ed `{plugin}`", ephemeral=True)


@plugin_.sub_command()
async def load(
    inter: CommandInteraction, ext: str | None = commands.Param(None, choices=KNOWN_PLUGIN_PATHS)
) -> None:
    """Load a plugin.

    Parameters
    ----------
    ext: The name of a plugin to perform action on.
    """
    await _plugin_helper(inter, ext, plugin.bot.load_extension, "load")


@plugin_.sub_command()
async def reload(
    inter: CommandInteraction, ext: str | None = commands.Param(None, choices=KNOWN_PLUGIN_PATHS)
) -> None:
    """Reload a plugin.

    Parameters
    ----------
    ext: The name of a plugin to perform action on.
    """
    await _plugin_helper(inter, ext, plugin.bot.reload_extension, "reload")


@plugin_.sub_command()
async def unload(
    inter: CommandInteraction, ext: str | None = commands.Param(None, choices=KNOWN_PLUGIN_PATHS)
) -> None:
    """Unload a plugin.

    Parameters
    ----------
    ext: The name of a plugin to perform action on.
    """
    await _plugin_helper(inter, ext, plugin.bot.unload_extension, "unload")


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
) -> NoReturn:
    """Explicitly raises chosen exception.

    Parameters
    ----------
    exception: Name of the exception to raise.
    message: Message passed to the exception.
    """
    if exception not in KNOWN_EXCEPTION_NAMES:
        raise commands.UserInputError("Unknown exception.")  # noqa: TRY003, EM101

    exc: type[commands.CommandError] = getattr(commands.errors, exception)
    await inter.response.defer()
    raise exc(message)


@force_error.autocomplete("exception")
def get_matching_exceptions(_: CommandInteraction, input: str) -> AutocompleteReturnType:
    if len(input) < 2:  # noqa: PLR2004
        return KNOWN_EXCEPTION_NAMES[: InteractionLimits.autocomplete_options]

    input = input.lower()
    matching: list[str] = []

    for exc in KNOWN_EXCEPTION_NAMES:
        if input in exc.lower():
            matching.append(exc)

            if len(matching) == InteractionLimits.autocomplete_options:
                break

    return matching


@plugin.slash_command()
@commands.default_member_permissions(administrator=True)
@commands.is_owner()
async def set_locale(
    inter: CommandInteraction,
    locale_name: str | None = commands.Param(None, name="locale"),
) -> None:
    """Override commands' locale.

    Parameters
    ----------
    locale: Locale code to override with.
    """
    if locale_name is None:
        i18n.remove_locale_override()
        msg = "Locale reset"

    else:
        try:
            locale = disnake.Locale[locale_name]

        except KeyError:
            msg = f"Unknown locale: {locale_name}"

        else:
            i18n.set_locale_override(locale)
            msg = f"Locale set to {locale_name}"

    plugin.logger.info(msg)
    await inter.response.send_message(msg)


@set_locale.autocomplete("locale")
async def get_matching_locale(_: CommandInteraction, input: str) -> AutocompleteReturnType:
    matching: list[str] = []

    if len(input) < 2:  # noqa: PLR2004
        return matching

    for locale in disnake.Locale:
        if input in locale.name:
            matching.append(locale.name)

            if len(matching) == InteractionLimits.autocomplete_options:
                break

    return matching


setup, teardown = plugin.create_extension_handlers()
