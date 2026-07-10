from typing import Final, Literal, NamedTuple

import anyio

import disnake
from discord import ComponentLimits, markdown as md, text_to_file
from disnake.ext import commands

from app import devtools, i18n, init, paths, ui
from app.assets import Colors
from app.core import AppState
from app.plugins_factory import create_dev_plugin
from app.typeshed import CommandInteraction
from app.utils import format_exception, walk_extensions

plugin = create_dev_plugin(__name__)
KNOWN_PLUGIN_PATHS = tuple(walk_extensions(paths.PLUGINS_PACKAGE))
assert 1 <= len(KNOWN_PLUGIN_PATHS) <= ComponentLimits.string_select_options


class ComponentIds:
    prefix: Final = "dev-console"

    locale_select: Final = "locale"
    i18n_button: Final = "rei18n"
    debug_button: Final = "debug"
    reset_button: Final = "reset"
    plugin_select: Final = "plugins"
    reload_button: Final = "reload"
    cmd_sync_button: Final = "cmdsync"

    type AnyId = Literal["locale", "rei18n", "debug", "reset", "plugins", "reload", "cmdsync"]


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

    locale_override = AppState.I18n.locale_override
    locale_options = [
        ui.SelectOption(
            label="None",
            value="$none",
            description="Select to remove the override",
            emoji="🏴‍☠️",
            default=locale_override is None,
        )
    ]
    locale_options += [
        ui.SelectOption(
            label=info.english_name
            if info.region is None
            else f"{info.english_name} - {info.region}",
            value=locale.name,
            description=info.local_name,
            emoji=info.flag_emoji,
            default=locale is locale_override,
        )
        for locale, info in AppState.I18n.locale_info.items()
    ]
    add_component(ui.Section(
        ui.TextDisplay("## Locale override"),
        accessory=ui.ActionButton(
            custom_id=make_component_id(ComponentIds.i18n_button, ctx),
            label="Reload i18n",
            emoji="🏳️",
        ),
    ))  # fmt: skip
    add_component(ui.ActionRow(ui.StringSelect(
        custom_id=make_component_id(ComponentIds.locale_select, ctx),
        placeholder="Select locale",
        options=locale_options,
    )))  # fmt: skip
    add_component(ui.Section(
        ui.TextDisplay("## Plugins"),
        accessory=ui.ActionButton(
            custom_id=make_component_id(ComponentIds.reload_button, ctx),
            style=ui.ButtonStyle.gray,
            label="Reload plugin",
            disabled=ctx.last_reload_plugin_name is None,
            emoji="🏗️",
        ),
    ))  # fmt: skip
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
async def slash_devtools(inter: CommandInteraction) -> None:
    """Open developer console."""
    ctx = DevtoolsUIContext(last_reload_plugin_name=AppState.recently_loaded_plugin)
    components = create_console(ctx)
    await inter.response.send_message(
        components=components, flags=disnake.MessageFlags(is_components_v2=True)
    )


@plugin.listener(disnake.Event.message_interaction)
async def _(inter: ui.MessageInteraction) -> None:
    if not inter.data.custom_id.startswith(ComponentIds.prefix):
        return

    if not await AppState.bot.is_owner(inter.author):
        await inter.response.send_message("You cannot use this.", ephemeral=True)
        return

    component, ctx = parse_component_id(inter.data.custom_id)
    error_container, add_err_component = ui.container(accent_color=Colors.error)
    files: list[disnake.File] = []

    match component:
        case ComponentIds.locale_select:
            assert inter.values
            [option_value] = inter.values

            if option_value == "$none":
                AppState.I18n.locale_override = None

            else:
                AppState.I18n.locale_override = disnake.Locale[option_value]

        case ComponentIds.i18n_button:
            i18n.load(paths.LOCALE_DIR)

        case ComponentIds.debug_button:
            AppState.debug_log_components ^= True

        case ComponentIds.reset_button:
            AppState.I18n.locale_override = None
            AppState.debug_log_components = False

        case ComponentIds.plugin_select:
            assert inter.values
            [option_value] = inter.values

            if option_value not in KNOWN_PLUGIN_PATHS:
                add_err_component(ui.TextDisplay("Selected plugin is no longer available."))

            else:
                AppState.recently_loaded_plugin = option_value
                ctx = ctx.__replace__(last_reload_plugin_name=option_value)

        case ComponentIds.cmd_sync_button:
            await init.sync_commands(AppState.bot)

        case ComponentIds.reload_button:
            if ctx.last_reload_plugin_name is None:
                add_err_component(ui.TextDisplay("Cannot reload, no cached plugin."))

            else:
                try:
                    AppState.bot.reload_extension(ctx.last_reload_plugin_name)

                except commands.ExtensionFailed as exc:
                    add_err_component(
                        ui.TextDisplay("## ⚠️ An exception occurred during reloading:")
                    )
                    traceback_text = format_exception(exc.original)

                    if md.codeblock_size(traceback_text) <= ComponentLimits.text_display_content:
                        add_err_component(ui.TextDisplay(md.codeblock(traceback_text)))

                    else:
                        files.append(traceback_file := text_to_file(traceback_text, "traceback.py"))
                        add_err_component(ui.file(traceback_file))

        case _:
            add_err_component(ui.TextDisplay("Unknown component"))
            plugin.logger.warning("%s - unknown component: %r", slash_devtools.name, component)

    components = create_console(ctx)
    if __debug__:
        devtools.debug_components(components)

    if error_container.children:
        async with anyio.create_task_group() as tg:
            tg.start_soon(lambda: inter.response.edit_message(components=components))
            tg.start_soon(
                lambda: inter.followup.send(
                    files=files,
                    components=error_container,
                    flags=disnake.MessageFlags(is_components_v2=True, ephemeral=True),
                )
            )

    else:
        await inter.response.edit_message(components=components)


setup, teardown = plugin.create_extension_handlers()
