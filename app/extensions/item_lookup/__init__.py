from __future__ import annotations

import typing as t

from disnake import CommandInteraction, Embed
from disnake.ext import commands, plugins

from bridges import AppContext, item_name_autocomplete
from config import TEST_GUILDS
from library_extensions import embed_image, sanitize_filename
from managers import renderer_manager

from .item_lookup import ItemCompareView, ItemView, compact_fields, default_fields

from supermechs.api import Element, ItemBase, Type  # noqa: TCH002
from supermechs.typedefs import LiteralElement, LiteralType, Name

if t.TYPE_CHECKING:
    LiteralTypeOrAny = LiteralType | t.Literal["ANY"]
    LiteralElementOrAny = LiteralElement | t.Literal["ANY"]

else:
    # disnake cannot parse unions of literals
    LiteralTypeOrAny = t.Literal[(*t.get_args(LiteralType), "ANY")]
    LiteralElementOrAny = t.Literal[(*t.get_args(LiteralElement), "ANY")]

plugin = plugins.Plugin["commands.InteractionBot"](name="Item-lookup", logger=__name__)


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    item: ItemBase,
    type: LiteralTypeOrAny = "ANY",
    element: LiteralElementOrAny = "ANY",
    compact: bool = False,
) -> None:
    """Finds an item and returns its stats. {{ ITEM }}

    Parameters
    -----------
    type: If provided, filters suggested names to given type. {{ ITEM_TYPE }}

    element: If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}

    compact: Whether the embed sent back should be compact (breaks on mobile). {{ ITEM_COMPACT }}
    """
    del type, element  # used for autocomplete only
    renderer = renderer_manager.mapping["@Darkstare"]
    image = renderer.get_item_sprite(item, item.transform_range.max).image
    url, file = embed_image(image, sanitize_filename(item.name, ".png"))

    if compact:
        # fmt: off
        embed = (
            Embed(color=item.element.color)
            .set_author(name=item.name, icon_url=item.type.image_url)
            .set_thumbnail(url)
        )
        # fmt: on
        field_factory = compact_fields

    else:
        # fmt: off
        embed = (
            Embed(
                title=item.name,
                description=f"{item.element.name.capitalize()} "
                f"{item.type.name.replace('_', ' ').lower()}",
                color=item.element.color,
            )
            .set_thumbnail(item.type.image_url)
            .set_image(url)
        )
        # fmt: on
        field_factory = default_fields

    view = ItemView(embed, item, field_factory, user_id=inter.author.id)
    await inter.response.send_message(embed=embed, file=file, view=view, ephemeral=True)

    await view.wait()
    await inter.edit_original_response(view=None)


@plugin.slash_command(guild_ids=TEST_GUILDS)
async def item_raw(
    inter: CommandInteraction,
    item: ItemBase,
    type: LiteralTypeOrAny = "ANY",
    element: LiteralElementOrAny = "ANY",
) -> None:
    """Finds an item and returns its raw stats. {{ ITEM }}

    Parameters
    ----------
    type: If provided, filters suggested names to given type. {{ ITEM_TYPE }}

    element: If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    """
    del type, element  # used for autocomplete only
    await inter.response.send_message(f"`{item!r:.1998}`", ephemeral=True)


def str_type(type: Type) -> str:
    return type.name.replace("_", " ").lower()


def str_elem(element: Element) -> str:
    return element.name.capitalize()


@plugin.slash_command()
async def compare(inter: CommandInteraction, context: AppContext, item1: Name, item2: Name) -> None:
    """Shows an interactive comparison of two items. {{ COMPARE }}

    Parameters
    ----------
    item1: First item to compare. {{ COMPARE_FIRST }}

    item2: Second item to compare. {{ COMPARE_SECOND }}
    """
    pack = context.client.default_pack

    try:
        item_a = pack.get_item_by_name(item1)
        item_b = pack.get_item_by_name(item2)

    except LookupError as err:
        raise commands.UserInputError(str(err)) from err

    if item_a.element is item_b.element:
        desc = str_elem(item_a.element)
        color = item_a.element.color

        if item_a.type is item_b.type:
            desc += " "
            desc += str_type(item_a.type)

            if not desc.endswith("s"):  # legs do end with s
                desc += "s"

        else:
            desc += f" {str_type(item_a.type)} / {str_type(item_b.type)}"

    else:
        desc = f"{str_elem(item_a.element)} {str_type(item_a.type)}"
        desc += f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    view = ItemCompareView(embed, item_a, item_b, user_id=inter.author.id)
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    await view.wait()
    await inter.edit_original_response(view=None)


compare.autocomplete("item1")(item_name_autocomplete)
compare.autocomplete("item2")(item_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
