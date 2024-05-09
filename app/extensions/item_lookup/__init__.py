import io
import typing

from disnake import CommandInteraction, Embed
from disnake.ext import commands, plugins
from disnake.utils import MISSING

from assets import ELEMENT, SIDED_TYPE, TYPE
from bridges import item_name_autocomplete
from bridges.embeds import sikrit_footer
from bridges.ui import get_check
from config import CONFIG
from discord_utils import MessageLimits
from discord_utils.ui.store import ComponentStore
from env import ENV
from shared.item_packs import DEFAULT_PACK, get_item_by_name

from .item_lookup import item_compare_view, item_view

from supermechs.api import Element, ItemData, Type
from supermechs.ext.deserializers.typedefs.packs import LiteralElement, LiteralType

if typing.TYPE_CHECKING:
    LiteralTypeOrAny = LiteralType | typing.Literal["ANY"]
    LiteralElementOrAny = LiteralElement | typing.Literal["ANY"]

else:
    # disnake cannot parse unions of literals
    LiteralTypeOrAny = typing.Literal[(*typing.get_args(LiteralType), "ANY")]
    LiteralElementOrAny = typing.Literal[(*typing.get_args(LiteralElement), "ANY")]

plugin = plugins.Plugin[commands.InteractionBot](name="Item-lookup", logger=__name__)


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    item: ItemData,
    type: LiteralTypeOrAny = "ANY",  # noqa: A002
    element: LiteralElementOrAny = "ANY",
    compact: bool = False,
) -> None:
    """Lookup item stats. {{ ITEM }}

    Parameters
    ----------
    type: Limits suggestions to chosen type. {{ ITEM_TYPE }}
    element: Limits suggestions to chosen element. {{ ITEM_ELEMENT }}
    compact: Compact layout. (broken on mobile) {{ ITEM_COMPACT }}
    """
    del type, element  # used for autocomplete only

    # _, renderer = get_default_pack()
    # sprite = renderer.get_item_sprite(item, get_final_stage(item.start_stage).tier)

    # if sprite.metadata.source == "url" and sprite.metadata.method == "single":
    #     url, file = sprite.metadata.value, MISSING

    # else:
        # await sprite.load()
        # url, file = embed_image(sprite.image, item.name)
    url, file = CONFIG.missing_image_url, MISSING  # FIXME

    embed_color = ELEMENT[item.element].color

    if item.type is Type.SIDE_WEAPON or item.type is Type.TOP_WEAPON:
        icon_url = SIDED_TYPE[item.type].right.image_url

    else:
        icon_url = TYPE[item.type].image_url

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

    sikrit_footer(embed, inter.locale)

    store = ComponentStore(interaction_check=get_check(inter.author))
    layout = item_view(store, embed, item, inter.locale, compact)
    await inter.response.send_message(embed=embed, file=file, components=layout, ephemeral=True)
    await store.listen(plugin.bot)
    await inter.edit_original_response(components=None)


@plugin.slash_command(guild_ids=ENV.test_guild_ids)
async def item_raw(
    inter: CommandInteraction,
    item: ItemData,
    type: LiteralTypeOrAny = "ANY",  # noqa: A002
    element: LiteralElementOrAny = "ANY",
) -> None:
    """Finds an item and returns its raw stats. {{ ITEM }}

    Parameters
    ----------
    type: If provided, filters suggested names to given type. {{ ITEM_TYPE }}
    element: If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    """
    del type, element  # used for autocomplete only
    await inter.response.send_message(f"`{item!r:.{MessageLimits.content - 2}}`", ephemeral=True)


def str_type(type: Type) -> str:  # noqa: A002
    return type.name.replace("_", " ").lower()


def str_elem(element: Element) -> str:
    return element.name.capitalize()


@plugin.slash_command()
async def compare(
    inter: CommandInteraction,
    item1_name: str = commands.Param(name="item1"),
    item2_name: str = commands.Param(name="item2"),
) -> None:
    """Interactive comparison between two items. {{ COMPARE }}

    Parameters
    ----------
    item1: First item to compare. {{ COMPARE_FIRST }}
    item2: Second item to compare. {{ COMPARE_SECOND }}
    """
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
        color = ELEMENT[item_a.element].color

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    sikrit_footer(embed, inter.locale)

    store = ComponentStore(interaction_check=get_check(inter.author))
    layout = item_compare_view(store, embed, item_a, item_b, inter.locale)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)
    await store.listen(plugin.bot)
    await inter.edit_original_response(components=None)


compare.autocomplete("item1")(item_name_autocomplete)
compare.autocomplete("item2")(item_name_autocomplete)


setup, teardown = plugin.create_extension_handlers()
