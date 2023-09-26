from __future__ import annotations

import io
import typing as t

from disnake import Attachment, CommandInteraction, Embed, File
from disnake.ext import commands, plugins
from disnake.ui import StringSelect
from disnake.utils import MISSING

from assets import ELEMENT, SIDED_TYPE, STAT, TYPE
from bridges import mech_name_autocomplete
from library_extensions import (
    OPTION_LIMIT,
    command_mention,
    debug_footer,
    embed_image,
    sikrit_footer,
)
from library_extensions.ui import wait_for_component
from managers import get_default_pack
from shared.utils import wrap_bytes
from user_input import sanitize_string

from .mech_manager import MechView

from supermechs.api import Player, Type
from supermechs.ext.workshop import dump_mechs, load_mechs

plugin = plugins.Plugin[commands.InteractionBot](name="Mech-manager", logger=__name__)


@plugin.load_hook(post=True)
async def on_load() -> None:
    await plugin.bot.wait_until_ready()
    buffs_command = plugin.bot.get_global_command_named("buffs")
    assert buffs_command is not None
    MechView.buffs_command = command_mention(buffs_command)


@plugin.slash_command()
async def mech(inter: CommandInteraction) -> None:
    del inter


MECH_SUMMARY_TEMPLATE = f"""\
• {TYPE[Type.TORSO].emoji} {{TORSO}}
• {TYPE[Type.LEGS].emoji} {{LEGS}}
• {SIDED_TYPE[Type.SIDE_WEAPON].right.emoji} {{WEAPONS}} weapon(s)
• {TYPE[Type.MODULE].emoji} {{MODULES}} module(s)
• {STAT['weight']} {{WEIGHT}} weight\
"""


@mech.sub_command(name="list")
async def browse(inter: CommandInteraction, player: Player) -> None:
    """Displays a list of your builds. {{ MECH_BROWSE }}"""
    if not player.builds:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.active_build is not None:
        embed.description = f"Currently active: **{player.active_build.name}**"

    fields: list[tuple[str, str]] = []

    for name, build in player.builds.items():
        value = MECH_SUMMARY_TEMPLATE.format(
            TORSO="no torso" if build.torso is None else build.torso.data.name,
            LEGS="no legs" if build.legs is None else build.legs.data.name,
            WEAPONS=sum(1 for _ in filter(None, build.iter_items("weapons"))),
            MODULES=sum(1 for _ in filter(None, build.modules)),
            WEIGHT=build.weight,
        )
        fields.append((name, value))

    for title, value in fields:
        embed.add_field(title, value)

    if __debug__:
        debug_footer(embed)

    await inter.send(embed=embed, ephemeral=True)


@mech.sub_command()
@commands.max_concurrency(1, commands.BucketType.user)
async def build(
    inter: CommandInteraction,
    player: Player,
    name: commands.String[str, 1, 32] | None = None,
) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    ----------
    name: The name of existing build or one to create.\
        If not passed, defaults to "Unnamed Mech". {{ MECH_BUILD_NAME }}
    """
    default_pack, renderer = await get_default_pack()

    if name is None:
        mech = player.get_active_or_create_build()

    else:
        mech = player.get_or_create_build(sanitize_string(name))

    view = MechView(
        mech=mech,
        pack=default_pack,
        renderer=renderer,
        player=player,
        locale=inter.locale,
        timeout=100,
    )
    file = MISSING

    if mech.torso is not None:
        view.embed.color = ELEMENT[mech.torso.data.element].color

        await renderer.load_mech_images(mech)
        image = renderer.create_mech_image(mech)
        url, file = embed_image(image, view.mech_config + ".png")
        view.embed.set_image(url)

    if __debug__:
        debug_footer(view.embed)

    else:
        sikrit_footer(view.embed)

    await inter.response.send_message(embed=view.embed, file=file, view=view, ephemeral=True)
    await view.wait()
    await inter.edit_original_response(view=None)


@mech.sub_command(name="import")
async def import_(inter: CommandInteraction, player: Player, file: Attachment) -> None:
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

    default_pack, _ = await get_default_pack()
    # TODO: make load_mechs ask for item packs
    data = await file.read()
    try:
        mechs, failed = load_mechs(data, default_pack)

    except (ValueError, TypeError) as err:
        raise commands.UserInputError(f"Parsing the file failed: {err}") from err

    string_builder = io.StringIO()

    if failed:
        string_builder.write("Failed to load:\n")
        for index, reason in failed:
            string_builder.write(f"{index}: {reason}\n")

    if mechs:
        # TODO: warn about overwriting
        player.builds.update((mech.name, mech) for mech in mechs)
        string_builder.write("Loaded mechs: ")
        string_builder.write(", ".join(f"`{mech.name}`" for mech in mechs))

    else:
        string_builder.write("No mechs loaded.")

    await inter.response.send_message(string_builder.getvalue(), ephemeral=True)


@mech.sub_command()
async def export(
    inter: CommandInteraction, player: Player, format: t.Literal["json", "toml"] = "json"
) -> None:
    """Export your mechs into a WU-compatible .JSON file. {{ MECH_EXPORT }}

    Parameters
    ----------
    format: The file format to output data in.\
        Formats other than .json are not supported by WU. {{ MECH_EXPORT_FORMAT }}
    """
    build_count = len(player.builds)

    if build_count == 0:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    default_pack, _ = await get_default_pack()

    if build_count == 1:
        fp = io.BytesIO(dump_mechs(player.builds.values(), default_pack.key))
        file = File(fp, "mechs.json")
        return await inter.response.send_message(file=file, ephemeral=True)

    # TODO: >25 mechs
    mech_select = StringSelect(
        placeholder="Select mechs to export",
        max_values=min(OPTION_LIMIT, build_count),
        options=list(player.builds)[:OPTION_LIMIT],
    )
    await inter.response.send_message(components=mech_select, ephemeral=True)

    try:
        new_inter = await wait_for_component(plugin.bot, mech_select, timeout=600)

    except TimeoutError:
        return await inter.delete_original_response()

    values = new_inter.values
    assert values is not None
    selected = frozenset(values)

    mechs = (mech for name, mech in player.builds.items() if name in selected)
    fp = io.BytesIO(dump_mechs(mechs, default_pack.key))
    file = File(fp, "mechs.json")
    await new_inter.response.edit_message(file=file, components=None)


build.autocomplete("name")(mech_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
