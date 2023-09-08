from __future__ import annotations

import io
import typing as t

import anyio
from disnake import CommandInteraction, Embed
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from assets import ELEMENT, SIDED_TYPE, TYPE
from bridges import item_name_autocomplete
from config import TEST_GUILDS
from events import PACK_LOADED
from library_extensions import MAX_RESPONSE_TIME, embed_image, sanitize_filename
from managers import item_pack_manager, renderer_manager

from .item_lookup import ItemCompareView, ItemView, compact_fields, default_fields

from supermechs.enums import Element, Type
from supermechs.ext.deserializers.typedefs import LiteralElement, LiteralType
from supermechs.models.item import ItemData  # noqa: TCH002

if t.TYPE_CHECKING:
    from supermechs.typedefs import Name

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
    item: ItemData,
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

    async with anyio.fail_after(MAX_RESPONSE_TIME - 0.5):
        await PACK_LOADED.wait()

    renderer = renderer_manager["@Darkstare"]  # TODO
    sprite = renderer.get_item_sprite(item, item.transform_range[-1])

    if sprite.metadata.source == "url" and sprite.metadata.method == "single":
        url, file = sprite.metadata.value, MISSING

    else:
        await sprite.load()
        url, file = embed_image(sprite.image, sanitize_filename(item.name, ".png"))

    embed_color = ELEMENT[item.element].color

    if item.type is Type.SIDE_WEAPON or item.type is Type.TOP_WEAPON:
        icon_url = SIDED_TYPE[item.type].right.image_url

    else:
        icon_url = TYPE[item.type].image_url

    if compact:
        # fmt: off
        embed = (
            Embed(color=embed_color)
            .set_author(name=item.name, icon_url=icon_url)
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
                color=embed_color,
            )
            .set_thumbnail(icon_url)
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
    item: ItemData,
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
async def compare(inter: CommandInteraction, item1: Name, item2: Name) -> None:
    """Shows an interactive comparison of two items. {{ COMPARE }}

    Parameters
    ----------
    item1: First item to compare. {{ COMPARE_FIRST }}
    item2: Second item to compare. {{ COMPARE_SECOND }}
    """
    async with anyio.fail_after(MAX_RESPONSE_TIME - 0.5):
        await PACK_LOADED.wait()

    pack = item_pack_manager["@Darkstare"]  # TODO

    try:
        item_a = pack.get_item_by_name(item1)
        item_b = pack.get_item_by_name(item2)

    except LookupError as err:
        raise commands.UserInputError(str(err)) from err


    if item_a.element is item_b.element:
        desc_builder = io.StringIO(str_elem(item_a.element))
        color = ELEMENT[item_a.element].color

        if item_a.type is item_b.type:
            desc_builder.write(" ")
            type_ = str_type(item_a.type)
            desc_builder.write(type_)

            if not type_.endswith("s"):  # legs do end with s
                desc_builder.write("s")

        else:
            desc_builder.write(f" {str_type(item_a.type)} / {str_type(item_b.type)}")

        desc = desc_builder.getvalue()

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    view = ItemCompareView(embed, item_a, item_b, user_id=inter.author.id)
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    await view.wait()
    await inter.edit_original_response(view=None)


compare.autocomplete("item1")(item_name_autocomplete)
compare.autocomplete("item2")(item_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
