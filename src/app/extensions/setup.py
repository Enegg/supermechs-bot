from typing import Final, Literal, NamedTuple

import disnake
from app.disnake_types import CommandInteraction
from discord import ComponentLimits, markdown as md, text_to_file
from discord.extensions import walk_extensions
from disnake.ext import commands

from app import devtools, paths, ui
from app.assets import Colors
from app.core import AppState
from app.plugins_factory import create_dev_plugin
from app.utils import format_exception

plugin = create_dev_plugin(__name__)
KNOWN_PLUGIN_PATHS = tuple(walk_extensions(paths.PLUGINS_PACKAGE))
assert 1 <= len(KNOWN_PLUGIN_PATHS) <= ComponentLimits.string_select_options


class ComponentIds:
    __slots__ = ()

    prefix: Final = "dev-console"

    locale_select: Final = "locale"
    debug_button: Final = "debug"
    reset_button: Final = "reset"
    plugin_select: Final = "plugins"
    reload_button: Final = "reload"
    cmd_sync_button: Final = "cmdsync"

    type AnyId = Literal["locale", "debug", "reset", "plugins", "reload", "cmdsync"]


class DevtoolsUIContext(NamedTuple):
    last_reload_plugin_name: str | None = None


def make_component_id(component: str, ctx: DevtoolsUIContext) -> str:
    plugin_name = "$none" if ctx.last_reload_plugin_name is None else ctx.last_reload_plugin_name
    return f"{ComponentIds.prefix}:{component}:{plugin_name}"


def parse_component_id(id: str, /) -> tuple[ComponentIds.AnyId | str, DevtoolsUIContext]:
    _, component, plugin_name = id.split(":", 2)
    ctx = DevtoolsUIContext(last_reload_plugin_name=None if plugin_name == "$none" else plugin_name)
    return component, ctx


def create_console(ctx: DevtoolsUIContext) -> ui.MessageComponents:
    container, add_component = ui.container()
    add_component(ui.TextDisplay("# Developer Console"))

    current_override = AppState.I18n.locale_override.unwrap_or(None)
    locale_options = [
        ui.SelectOption(
            label="None",
            value="$none",
            description="Select to remove the override",
            emoji="🏴‍☠️",
            default=current_override is None,
        )
    ]
    locale_options += [
        ui.SelectOption(
            label=(
                info.region
                .map(lambda region, info=info: f"{info.english_name} - {region}")
                .unwrap_or(info.english_name)
            ),
            value=locale.name,
            description=info.local_name,
            emoji=info.flag_emoji.unwrap_or(None),
            default=locale is current_override,
        )
        for locale, info in AppState.I18n.locale_info.items()
    ]  # fmt: skip
    add_component(ui.TextDisplay("## Locale override"))
    add_component(ui.ActionRow(ui.StringSelect(
        custom_id=make_component_id(ComponentIds.locale_select, ctx),
        placeholder="Select locale",
        options=locale_options,
    )))  # fmt: skip
    add_component(ui.TextDisplay("## Plugins"))
    add_component(ui.ActionRow(ui.StringSelect(
        custom_id=make_component_id(ComponentIds.plugin_select, ctx),
        placeholder="Select plugin to reload",
        options=[
            ui.SelectOption(label=plugin_name, default=plugin_name == ctx.last_reload_plugin_name)
            for plugin_name in KNOWN_PLUGIN_PATHS
        ],
    )))  # fmt: skip
    add_component(ui.ActionRow(
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.reload_button, ctx),
            style=ui.ButtonStyle.gray,
            label="Reload plugin",
            disabled=ctx.last_reload_plugin_name is None,
            emoji="🏗️",
        ),
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.cmd_sync_button, ctx),
            style=ui.ButtonStyle.gray,
            label="Sync commands",
            emoji="💱",
        )
    ))  # fmt: skip
    add_component(ui.Separator(divider=True))
    add_component(ui.ActionRow(
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.debug_button, ctx),
            style=ui.ButtonStyle.green if AppState.debug_log_components else ui.ButtonStyle.gray,
            label="Debug components",
            emoji="🗒️",
        ),
        ui.ActionButton(
            custom_id=make_component_id(ComponentIds.reset_button, ctx),
            style=ui.ButtonStyle.red,
            label="Reset",
            emoji="🔙",
        ),
    ))  # fmt: skip
    return container


@plugin.slash_command(name="devtools")
@commands.is_owner()
async def dev_console(inter: CommandInteraction) -> None:
    """Open developer console."""
    ctx = DevtoolsUIContext(last_reload_plugin_name=AppState.recently_loaded_plugin)
    components = create_console(ctx)
    await inter.response.send_message(
        components=components, flags=disnake.MessageFlags(is_components_v2=True)
    )


@plugin.listener(disnake.Event.message_interaction)
async def on_console_interaction(inter: ui.MessageInteraction) -> None:
    if not inter.data.custom_id.startswith(ComponentIds.prefix):
        return

    if not await AppState.bot.is_owner(inter.author):
        await inter.response.send_message("You cannot use this.", ephemeral=True)
        return

    component, ctx = parse_component_id(inter.data.custom_id)
    error_container = ui.Container(accent_colour=Colors.error)
    traceback_file: disnake.File = disnake.utils.MISSING

    match component:
        case ComponentIds.locale_select:
            assert inter.values
            [option_value] = inter.values

            if option_value == "$none":
                AppState.I18n.remove_locale_override()

            else:
                AppState.I18n.set_locale_override(disnake.Locale[option_value])

        case ComponentIds.debug_button:
            AppState.debug_log_components ^= True

        case ComponentIds.reset_button:
            AppState.I18n.remove_locale_override()
            AppState.debug_log_components = False

        case ComponentIds.plugin_select:
            assert inter.values
            [option_value] = inter.values

            if option_value not in KNOWN_PLUGIN_PATHS:
                error_container.children.append(
                    ui.TextDisplay("Selected plugin is no longer available.")
                )

            else:
                AppState.recently_loaded_plugin = option_value
                ctx = ctx.__replace__(last_reload_plugin_name=option_value)

        case ComponentIds.cmd_sync_button:
            from app.commands import sync

            await sync.sync_commands(AppState.bot)

        case ComponentIds.reload_button:
            if ctx.last_reload_plugin_name is None:
                error_container.children.append(ui.TextDisplay("Cannot reload, no cached plugin."))

            else:
                try:
                    AppState.bot.reload_extension(ctx.last_reload_plugin_name)

                except commands.ExtensionFailed as exc:
                    error_container.children.append(
                        ui.TextDisplay("## ⚠️ An exception occurred during reloading:")
                    )
                    traceback_text = format_exception(exc)

                    if md.codeblock_size(traceback_text) <= ComponentLimits.text_display_content:
                        error_container.children.append(
                            ui.TextDisplay(md.codeblock(traceback_text))
                        )

                    else:
                        traceback_file = text_to_file(traceback_text, "traceback.py")
                        error_container.children.append(ui.file(traceback_file))

        case _:
            error_container.children.append(ui.TextDisplay("Unknown component"))
            plugin.logger.warning("%s - unknown component: %r", dev_console.name, component)

    components = create_console(ctx)
    if __debug__:
        devtools.debug_components(components)
    await inter.response.edit_message(components=components)

    if error_container.children:
        await inter.followup.send(
            file=traceback_file,
            components=error_container,
            flags=disnake.MessageFlags(is_components_v2=True, ephemeral=True),
        )


setup, teardown = plugin.create_extension_handlers()
