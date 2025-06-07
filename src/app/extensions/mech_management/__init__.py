from collections import abc

from app.disnake_types import CommandInteraction
from discord import markdown as md
from discord.commands import register_cancellable
from disnake import Embed
from disnake.ext import commands
from disnake.utils import MISSING

from app import i18n, ui
from app.assets import EMOJIS
from app.commands.autocompleters import mech_name_autocomplete
from app.core import CONFIG
from app.devtools import debug_message
from app.embed_utils import embed_image, sikrit_footer
from app.managers import players
from app.models.item import HasStats
from app.plugins_factory import create_plugin
from app.text_utils import StringLimits, sanitize_string
from defer import Defer

from .mech_manager import MechView, embed_mech

import dupermechs.all as sm

plugin = create_plugin(__name__)


@plugin.load_hook(post=True)
async def on_load() -> None:
    from app.commands import sync

    # wait until API command caches are populated
    await sync.SYNC_FINISHED.wait()
    buffs_command = plugin.bot.get_global_command_named("buffs")

    if buffs_command is not None:
        MechView.buffs_mention = md.command_mention(buffs_command)


@plugin.slash_command()
async def mech(inter: CommandInteraction) -> None:
    del inter


# TODO: localize this
MECH_SUMMARY_TEMPLATE = f"""\
- {EMOJIS.types.torso} {{TORSO}}
- {EMOJIS.types.legs} {{LEGS}}
- {EMOJIS.types.right_side_weapon} `{{WEAPONS}}` weapon(s)
- {EMOJIS.types.module} `{{MODULES}}` module(s)
- {EMOJIS.stats.weight} `{{WEIGHT}}`kg\
"""


def count_weapons(mech: sm.IMech[object], /) -> int:
    return (
        int(mech.side_weapon_1 is not None)
        + int(mech.side_weapon_2 is not None)
        + int(mech.side_weapon_3 is not None)
        + int(mech.side_weapon_4 is not None)
        + int(mech.top_weapon_1 is not None)
        + int(mech.top_weapon_2 is not None)
    )


def count_modules(mech: sm.IMech[object], /) -> int:
    return (
        int(mech.module_1 is not None)
        + int(mech.module_2 is not None)
        + int(mech.module_3 is not None)
        + int(mech.module_4 is not None)
        + int(mech.module_5 is not None)
        + int(mech.module_6 is not None)
        + int(mech.module_7 is not None)
        + int(mech.module_8 is not None)
    )


def iter_items[T](mech: sm.IMech[T], /) -> abc.Iterator[T]:
    for slot in sm.Mech.Slot:
        if (item := mech[slot]) is not None:
            yield item


def get_weight(mech: sm.IMech[HasStats], /) -> int:
    return sum(item.stats.weight for item in iter_items(mech))


@mech.sub_command()
async def catalog(inter: CommandInteraction) -> None:
    """Catalog of your builds. {{ MECH_BROWSE }}"""  # noqa: D400
    player = players.get_or_create_player_from_user(inter.author)

    if not player.has_builds():
        return await inter.response.send_message("You do not have any builds.", ephemeral=True)

    embed = Embed(title="Your builds", color=inter.author.color)

    if player.recent_build is not None:
        embed.description = f"Currently active: **{player.recent_build.name}**"

    fields: list[tuple[str, str]] = []

    for build in player.iter_builds():
        mech = build.mech
        value = MECH_SUMMARY_TEMPLATE.format(
            TORSO="no torso" if mech.torso is None else mech.torso.name,
            LEGS="no legs" if mech.legs is None else mech.legs.name,
            WEAPONS=count_weapons(mech),
            MODULES=count_modules(mech),
            WEIGHT=get_weight(mech),
        )
        fields.append((build.name, value))

    # TODO: paginate
    for title, value in fields:
        embed.add_field(title, value)

    if __debug__:
        debug_message(embed)

    await inter.send(embed=embed, ephemeral=True)


@register_cancellable
@mech.sub_command()
async def build(
    inter: CommandInteraction,
    name: commands.String[str, 1, StringLimits.names] = commands.Param(
        "", autocomplete=mech_name_autocomplete
    ),
) -> None:
    """Interactive UI for modifying a mech build. {{ MECH_BUILD }}

    Parameters
    ----------
    name:
        The name of an existing build or of one to create. {{ MECH_BUILD_NAME }}
    """  # noqa: D400
    player = players.get_or_create_player_from_user(inter.author)

    if name == "":
        if (build := player.recent_build) is None:
            build = player.create_build()

    else:
        for build in player.builds.values():
            if build.name == name:
                break

        else:
            build = player.create_build(sanitize_string(name))

    locale = i18n.get_locale(inter)
    store = ui.callback_store(inter)
    view = MechView(store, build, player, locale)
    embed = embed_mech(build, locale)
    file = MISSING

    if False:  # FIXME
        if build.mech.torso is not None:
            renderer = object()
            await renderer.load_mech_images(mech)
            image = renderer.create_mech_image(mech)
            url, file = embed_image(image, view.mech_config)
            view.embed.set_image(url)

    sikrit_footer(embed, locale)

    if __debug__:
        debug_message(embed)

    await inter.response.send_message(
        embed=embed, file=file, components=view.paginator.page, ephemeral=True
    )
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.user_input_timeout)


setup, teardown = plugin.create_extension_handlers()
