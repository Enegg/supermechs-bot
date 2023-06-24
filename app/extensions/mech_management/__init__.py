from __future__ import annotations

import asyncio
import io
import typing as t

from disnake import Attachment, CommandInteraction, Embed, File
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from bridges import mech_name_autocomplete
from bridges.context import AppContext
from library_extensions import OPTION_LIMIT, command_mention, embed_image, embed_to_footer
from library_extensions.ui import Select, wait_for_component
from managers import player_manager, renderer_manager
from shared.utils import wrap_bytes

from .mech_manager import MechView

from supermechs.api import STATS, Player, Type, sanitize_name
from supermechs.ext.workshop.wu_compat import dump_mechs, load_mechs

if t.TYPE_CHECKING:
    from library_extensions.bot import ModularBot  # noqa: F401

plugin = plugins.Plugin["ModularBot"](name="Mech-manager", logger=__name__)


@plugin.load_hook(post=True)
async def on_load() -> None:
    await plugin.bot.wait_until_ready()
    buffs_command = plugin.bot.get_global_command_named("buffs")
    assert buffs_command is not None
    MechView.buffs_command = command_mention(buffs_command)


@plugin.slash_command()
async def mech(inter: CommandInteraction) -> None:
    del inter


@mech.sub_command(name="list")
async def browse(inter: CommandInteraction, player: Player) -> None:
    """Displays a list of your builds. {{ MECH_BROWSE }}"""
    if not player.builds:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.active_build is not None:
        embed.description = f"Currently active: **{player.active_build.name}**"

    fields: list[tuple[str, str]] = []

    def count_not_none(it: t.Iterable[t.Any | None]) -> int:
        return sum(1 for item in it if item is not None)

    template = (
        f"• {Type.TORSO.emoji} {{TORSO}}\n"
        f"• {Type.LEGS.emoji} {{LEGS}}\n"
        f"• {Type.SIDE_WEAPON.right.emoji} {{WEAPONS}} weapon(s)\n"
        f"• {Type.MODULE.emoji} {{MODULES}} module(s)\n"
        f"• {STATS['weight'].emoji} {{WEIGHT}} weight"
    )

    for name, build in player.builds.items():
        value = template.format(
            TORSO="no torso" if build.torso is None else build.torso.name,
            LEGS="no legs" if build.legs is None else build.legs.name,
            WEAPONS=count_not_none(build.iter_items(weapons=True)),
            MODULES=count_not_none(build.iter_items(modules=True)),
            WEIGHT=build.weight,
        )
        fields.append((name, value))

    for title, value in fields:
        embed.add_field(title, value)

    await inter.send(embed=embed, ephemeral=True)


@mech.sub_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def build(
    inter: CommandInteraction,
    context: AppContext,
    name: commands.String[str, 1, 32] | None = None,
) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    ----------
    name:
        The name of existing build or one to create.
        If not passed, defaults to "Unnamed Mech". {{ MECH_BUILD_NAME }}
    """
    player = player_manager.lookup_or_create(inter.author)
    renderer = renderer_manager.mapping["@Darkstare"]

    if name is None:
        mech = player.get_active_or_create_build()

    else:
        mech = player.get_or_create_build(sanitize_name(name))

    view = MechView(
        mech=mech,
        pack=context.client.default_pack,
        renderer=renderer,
        player=player,
        timeout=100,
    )
    file = MISSING

    if mech.torso is not None:
        view.embed.color = mech.torso.element.color

        image = renderer.get_mech_image(mech)
        url, file = embed_image(image, view.mech_config + ".png")
        view.embed.set_image(url)

    if __debug__:
        embed_to_footer(view.embed)

    await inter.response.send_message(embed=view.embed, file=file, view=view, ephemeral=True)
    await view.wait()
    await inter.edit_original_response(view=None)


@mech.sub_command(name="import")
async def import_(inter: CommandInteraction, context: AppContext, file: Attachment) -> None:
    """Import mech(s) from a .JSON file. {{ MECH_IMPORT }}

    Parameters
    ----------
    file: A .JSON file as exported from WU. {{ MECH_IMPORT_FILE }}
    """
    # file size of 64KiB sounds like a pretty beefy amount of mechs
    MAX_SIZE = 1 << 16

    if file.size > MAX_SIZE:
        size, unit = wrap_bytes(MAX_SIZE)
        raise commands.UserInputError(f"The maximum accepted file size is {size}{unit}.")
    # we could assert that content type is application/json, but we may just as well
    # rely on the loader to fail

    # TODO: make load_mechs ask for item packs
    try:
        mechs, failed = load_mechs(await file.read(), context.client.default_pack)

    except (ValueError, TypeError) as err:
        raise commands.UserInputError(f"Parsing the file failed: {err}") from err

    string_builder = io.StringIO()

    if failed:
        string_builder.write("Failed to load:\n")
        for index, reason in failed:
            string_builder.write(f"{index}: {reason}\n")

    if mechs:
        # TODO: warn about overwriting
        context.player.builds.update((mech.name, mech) for mech in mechs)
        string_builder.write("Loaded mechs: ")
        string_builder.write(", ".join(f"`{mech.name}`" for mech in mechs))

    else:
        string_builder.write("No mechs loaded.")

    await inter.response.send_message(string_builder.getvalue(), ephemeral=True)


@mech.sub_command()
async def export(inter: CommandInteraction, context: AppContext) -> None:
    """Export your mechs into a WU-compatible .JSON file. {{ MECH_EXPORT }}"""

    player = player_manager.lookup_or_create(inter.author)
    build_count = len(player.builds)

    if build_count == 0:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    if build_count == 1:
        fp = io.BytesIO(dump_mechs(player.builds.values(), context.client.default_pack.key))
        file = File(fp, "mechs.json")
        return await inter.response.send_message(file=file, ephemeral=True)

    mech_select = Select(
        placeholder="Select mechs to export",
        custom_id="select:exported_mechs",
        max_values=min(OPTION_LIMIT, build_count),
        options=list(player.builds)[:OPTION_LIMIT],
    )
    await inter.response.send_message(components=mech_select, ephemeral=True)

    try:
        new_inter = await wait_for_component(plugin.bot, mech_select, timeout=600)

    except asyncio.TimeoutError:
        return await inter.delete_original_response()

    values = new_inter.values
    assert values is not None
    selected = frozenset(values)

    mechs = (mech for name, mech in player.builds.items() if name in selected)
    fp = io.BytesIO(dump_mechs(mechs, context.client.default_pack.key))
    file = File(fp, "mechs.json")
    await new_inter.response.edit_message(file=file, components=None)


build.autocomplete("name")(mech_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
