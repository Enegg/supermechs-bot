import io
from typing import TYPE_CHECKING, Literal, get_args as get_type_args

from discord import MessageLimits
from disnake import CommandInteraction, Embed, Locale
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from app import paths
from app.assets import ASSETS
from app.bridges import embed_image, item_name_autocomplete, sikrit_footer, ui
from app.core import ENV
from app.shared.item_packs import DEFAULT_PACK, get_item_by_name

from .item_lookup import item_compare_view, item_view

from supermechs.api import Element, ItemData, Type
from supermechs.ext.deserializers.typedefs.packs import LiteralElement, LiteralType

if TYPE_CHECKING:
    LiteralTypeOrAny = LiteralType | Literal["ANY"]
    LiteralElementOrAny = LiteralElement | Literal["ANY"]

else:
    # disnake cannot parse unions of literals
    LiteralTypeOrAny = Literal[(*get_type_args(LiteralType), "ANY")]
    LiteralElementOrAny = Literal[(*get_type_args(LiteralElement), "ANY")]

plugin = plugins.Plugin[commands.InteractionBot](name="Item-lookup", logger=__name__)


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    locale: Locale,
    item: ItemData,
    type: LiteralTypeOrAny = "ANY",  # noqa: A002
    element: LiteralElementOrAny = "ANY",
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
    del type, element  # used for autocomplete only

    if False:  # FIXME: waiting for renderer
        _, renderer = get_default_pack()
        sprite = renderer.get_item_sprite(item, get_final_stage(item.start_stage).tier)

        if sprite.metadata.source == "url" and sprite.metadata.method == "single":
            url, file = sprite.metadata.value, MISSING

        else:
            await sprite.load()
            url, file = embed_image(sprite.image, item.name)

    else:
        from PIL import Image

        image = Image.open(paths.SILHOUETTE)
        url, file = embed_image(image, item.name)

    embed_color = ASSETS.elements[item.element.name].color

    if item.type is Type.SIDE_WEAPON or item.type is Type.TOP_WEAPON:
        icon_url = ASSETS.sided_types[item.type.name].right.image_url

    else:
        icon_url = ASSETS.types[item.type.name].image_url

    if compact:
        embed = (
            Embed(color=embed_color)
            .set_author(name=item.name, icon_url=icon_url)
            .set_thumbnail(url)
        )  # fmt: skip

    else:
        embed = (
            Embed(
                title=item.name,
                description=f"{item.element.name.capitalize()} "
                f"{item.type.name.replace('_', ' ').lower()}",
                color=embed_color,
            )
            .set_thumbnail(icon_url)
            .set_image(url)
        )  # fmt: skip

    sikrit_footer(embed, locale)

    store = ui.CallbackStore()
    layout = item_view(store, embed, item, locale, compact)
    await inter.response.send_message(embed=embed, file=file, components=layout, ephemeral=True)
    await store.listen(plugin.bot.wait_for, check=ui.get_check(inter.author))
    await inter.edit_original_response(components=None)


@plugin.slash_command(guild_ids=ENV.test_guild_ids)
async def item_raw(
    inter: CommandInteraction,
    item: ItemData,
    type: LiteralTypeOrAny = "ANY",  # noqa: A002
    element: LiteralElementOrAny = "ANY",
) -> None:
    """Lookup raw item stats. {{ ITEM }}

    Parameters
    ----------
    type:
        If provided, filters suggested names to given type. {{ ITEM_TYPE }}
    element:
        If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    """  # noqa: D400
    del type, element  # used for autocomplete only
    await inter.response.send_message(f"`{item!r:.{MessageLimits.content - 2}}`", ephemeral=True)


def str_type(type: Type) -> str:  # noqa: A002
    return type.name.replace("_", " ").lower()


def str_elem(element: Element) -> str:
    return element.name.capitalize()


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
    pack = DEFAULT_PACK.get_nowait()
    item_a = get_item_by_name(pack.items, item1_name)
    item_b = get_item_by_name(pack.items, item2_name)

    if item_a is None or item_b is None:
        raise commands.UserInputError  # TODO

    if item_a.element is item_b.element:
        desc_builder = io.StringIO()
        desc_builder.write(str_elem(item_a.element))

        if item_a.type is item_b.type:
            desc_builder.write(" ")
            type_ = str_type(item_a.type)
            desc_builder.write(type_)

            if not type_.endswith("s"):  # legs do end with s
                desc_builder.write("s")

        else:
            desc_builder.write(f" {str_type(item_a.type)} / {str_type(item_b.type)}")

        desc = desc_builder.getvalue()
        color = ASSETS.elements[item_a.element.name].color

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    sikrit_footer(embed, locale)

    store = ui.CallbackStore()
    layout = item_compare_view(store, embed, item_a, item_b, locale)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)
    await store.listen(plugin.bot.wait_for, check=ui.get_check(inter.author))
    await inter.edit_original_response(components=None)


setup, teardown = plugin.create_extension_handlers()
