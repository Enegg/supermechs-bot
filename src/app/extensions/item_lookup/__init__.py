import io

from app.disnake_types import CommandInteraction
from discord import MessageLimits
from disnake import Embed, Locale
from disnake.ext import commands
from disnake.utils import MISSING

from app.assets import ASSETS
from app.bridges import ui
from app.bridges.all import embed_image, sikrit_footer
from app.bridges.sm_utils import get_item_by_name, get_item_icon, get_item_pack_for
from app.commands.autocompleters import item_name_autocomplete
from app.commands.params import ELEMENT_CHOICES, TYPE_CHOICES
from app.core import CONFIG
from app.plugins_factory import create_plugin
from defer import Defer

from .item_lookup import item_compare_view, item_view

from supermechs.all import ItemData, abc as smabc

plugin = create_plugin(__name__)


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    locale: Locale,
    item: ItemData,
    type: str = commands.Param("ANY", choices=TYPE_CHOICES),  # noqa: A002
    element: str = commands.Param("ANY", choices=ELEMENT_CHOICES),
    compact: bool = False,
) -> None:
    """Lookup item stats. {{ ITEM }}

    Parameters
    ----------
    type:
        Limits suggestions to chosen type. {{ ITEM_TYPE }}
    element:
        Limits suggestions to chosen element. {{ ITEM_ELEMENT }}
    compact:
        Compact layout. (broken on mobile) {{ ITEM_COMPACT }}
    """  # noqa: D400
    item_pack = get_item_pack_for(inter)
    sprite = item_pack.get_sprite(item.id, item.stages[-1].tier)

    if sprite.url is not None:
        url, file = sprite.url, MISSING

    else:
        url, file = embed_image(await sprite.load(), item.name)

    embed_color = ASSETS.elements[item.element].color
    icon_url = get_item_icon(item).uri

    if compact:
        embed = (
            Embed(color=embed_color)
            .set_author(name=item.name, icon_url=icon_url)
            .set_thumbnail(url)
        )

    else:
        desc = f"{item.element.capitalize()} {item.type.replace('_', ' ').lower()}"
        embed = (
            Embed(title=item.name, description=desc, color=embed_color)
            .set_thumbnail(icon_url)
            .set_image(url)
        )

    sikrit_footer(embed, locale)

    store = ui.callback_store(inter)
    layout = item_view(store, embed, item, locale, compact)
    await inter.response.send_message(embed=embed, file=file, components=layout, ephemeral=True)
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.command_timeout)


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def item_raw(
    inter: CommandInteraction,
    item: ItemData,
    type: str = commands.Param("ANY", choices=TYPE_CHOICES),  # noqa: A002
    element: str = commands.Param("ANY", choices=ELEMENT_CHOICES),
) -> None:
    """Lookup raw item stats. {{ ITEM }}

    Parameters
    ----------
    type:
        If provided, filters suggested names to given type. {{ ITEM_TYPE }}
    element:
        If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    """  # noqa: D400
    await inter.response.send_message(f"`{item!r:.{MessageLimits.content - 2}}`", ephemeral=True)


def str_type(type: smabc.ItemType) -> str:  # noqa: A002
    return type.replace("_", " ").lower()


def str_elem(element: smabc.ItemElement) -> str:
    return element.capitalize()


@plugin.slash_command()
async def compare(
    inter: CommandInteraction,
    locale: Locale,
    item1_name: str = commands.Param(name="item1", autocomplete=item_name_autocomplete),
    item2_name: str = commands.Param(name="item2", autocomplete=item_name_autocomplete),
) -> None:
    """Interactive comparison between two items. {{ COMPARE }}

    Parameters
    ----------
    item1_name:
        First item to compare. {{ COMPARE_FIRST }}
    item2_name:
        Second item to compare. {{ COMPARE_SECOND }}
    """  # noqa: D400
    item_pack = get_item_pack_for(inter)
    item_a = get_item_by_name(item_pack.items.values(), item1_name)
    item_b = get_item_by_name(item_pack.items.values(), item2_name)

    if item_a is None or item_b is None:
        raise commands.UserInputError  # TODO

    if item_a.element == item_b.element:
        desc_builder = io.StringIO()
        desc_builder.write(str_elem(item_a.element))

        if item_a.type == item_b.type:
            desc_builder.write(" ")
            type_ = str_type(item_a.type)
            desc_builder.write(type_)

            if not type_.endswith("s"):  # legs do end with s
                desc_builder.write("s")

        else:
            desc_builder.write(f" {str_type(item_a.type)} / {str_type(item_b.type)}")

        desc = desc_builder.getvalue()
        color = ASSETS.elements[item_a.element].color

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    sikrit_footer(embed, locale)

    store = ui.callback_store(inter)
    layout = item_compare_view(store, embed, item_a, item_b, locale)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.command_timeout)


setup, teardown = plugin.create_extension_handlers()
