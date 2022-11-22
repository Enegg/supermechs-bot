from __future__ import annotations

import json
import logging
import typing as t

from disnake import Attachment, CommandInteraction, Embed, File, MessageInteraction
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from library_extensions import image_to_file
from ui import Select

from .mech_manager import MechView

from SuperMechs.core import STATS
from SuperMechs.enums import Type
from SuperMechs.ext.wu_compat import dump_mechs, load_mechs, mech_to_id_str
from SuperMechs.player import Player
from SuperMechs.utils import truncate_name

if t.TYPE_CHECKING:
    from bot import SMBot

LOGGER = logging.getLogger(__name__)
plugin = plugins.Plugin["SMBot"](name="Mech-manager")

MixedInteraction = CommandInteraction | MessageInteraction


@plugin.slash_command()
async def mech(_: CommandInteraction) -> None:
    pass


@mech.sub_command(name="list")
async def browse(inter: CommandInteraction, player: Player) -> None:
    """Displays a list of your builds. {{ MECH_BROWSE }}"""
    if not player.builds:
        await inter.send("You do not have any builds.", ephemeral=True)
        return

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.active_build_name:
        embed.description = f"Currently active: **{player.active_build_name}**"

    fields: list[tuple[str, str]] = []

    def count_not_none(it: t.Iterable[t.Any | None]) -> int:
        i = 0
        for item in it:
            if item is not None:
                i += 1
        return i

    fmt_string = (
        f"• {Type.TORSO.emoji} {{TORSO}}\n"
        f"• {Type.LEGS.emoji} {{LEGS}}\n"
        f"• {Type.SIDE_WEAPON.emoji} {{WEAPONS}} weapon(s)\n"
        f"• {Type.MODULE.emoji} {{MODULES}} module(s)\n"
        f"• {STATS['weight'].emoji} {{WEIGHT}} weight"
    )

    for name, build in player.builds.items():
        value = fmt_string.format(
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
async def build(inter: MixedInteraction, player: Player, name: str | None = None) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    -----------
    name: The name of existing build or one to create. If not passed, defaults to "Unnamed Mech". {{ MECH_BUILD_NAME }}
    """

    if name is None:
        mech = player.get_or_create_active_build()
        name = player.active_build_name

    elif name not in player.builds:
        mech = player.create_build(name)

    else:
        mech = player.builds[name]
        player.active_build_name = mech.name

    view = MechView(mech, plugin.bot.default_pack, player, timeout=100)
    file = MISSING

    if mech.torso is not None:
        view.embed.color = mech.torso.element.color

        file = image_to_file(mech.image, mech_to_id_str(mech))
        url = f"attachment://{file.filename}"
        view.embed.set_image(url)

    if isinstance(inter, MessageInteraction):
        await inter.response.edit_message(embed=view.embed, file=file, view=view)

    else:
        await inter.response.send_message(embed=view.embed, file=file, view=view, ephemeral=True)

    await view.wait()
    await inter.edit_original_response(view=None)


@mech.sub_command(name="import")
async def import_(inter: CommandInteraction, player: Player, file: Attachment) -> None:
    """Import mech(s) from a .JSON file.

    Parameters
    ----------
    file: a .JSON file as exported from WU.
    """
    # file size of 16KiB sounds like a pretty beefy amount of mechs
    MAX_SIZE = 1 << 14

    if MAX_SIZE < file.size:
        raise commands.UserInputError(f"The maximum accepted file size is {MAX_SIZE >> 10}KiB.")

    data = json.loads(await file.read())

    try:
        mechs, failed = load_mechs(data, plugin.bot.default_pack)

    except ValueError as e:
        raise commands.UserInputError(str(e)) from None

    if not mechs:
        message = "No mechs loaded."

    else:
        # TODO: warn about overwriting
        player.builds.update((mech.name, mech) for mech in mechs)
        message = "Loaded mechs: " + ", ".join(f"`{mech.name}`" for mech in mechs)

    if failed:
        message += "\nFailed to load: " + ", ".join(
            f"{name}, reason: {reason}" for name, reason in failed.items()
        )

    await inter.response.send_message(message, ephemeral=True)


@mech.sub_command()
async def export(inter: CommandInteraction, player: Player) -> None:
    """Export selected mechs into a WU-compatible .JSON file."""

    if not player.builds:
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    mech_select = Select(
        placeholder="Select mechs to export",
        custom_id="select:exported_mechs",
        max_values=min(25, len(player.builds)),
        options=list(player.builds)[:25],
    )
    await inter.response.send_message(components=mech_select, ephemeral=True)

    def check(inter: MessageInteraction) -> bool:
        return inter.data.custom_id == mech_select.custom_id

    new_inter: MessageInteraction = await plugin.bot.wait_for("dropdown", check=check)
    values = new_inter.values
    assert values is not None
    selected = frozenset(values)

    mechs = (mech for name, mech in player.builds.items() if name in selected)
    fp = dump_mechs(mechs, plugin.bot.default_pack.key)
    file = File(fp, "mechs.json")  # type: ignore
    await new_inter.response.edit_message(file=file, components=None)


@build.autocomplete("name")
async def mech_name_autocomplete(
    inter: CommandInteraction, input: str
) -> list[str] | dict[str, str]:
    """Autocomplete for player builds."""
    player = plugin.bot.get_player(inter)
    input = truncate_name(input)
    case_insensitive = input.lower()
    return (
        [name for name in player.builds if name.lower().startswith(case_insensitive)]
        or {f'Enter to create mech "{input}"...': input}
        if input
        else []
    )


setup, teardown = plugin.create_extension_handlers()