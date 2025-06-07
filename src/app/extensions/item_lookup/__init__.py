import io
from collections import abc

from monads.result import Err, Ok

from app.disnake_types import CommandInteraction
from discord import MessageLimits
from disnake import Embed, File
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, get_slot_icon
from app.commands.autocompleters import item_name_autocomplete
from app.commands.params import ELEMENT_CHOICES, TIER_CHOICES, TYPE_CHOICES
from app.core import CONFIG
from app.devtools import debug_message
from app.embed_utils import embed_file_resource, embed_image, sikrit_footer
from app.managers import gfx, packs
from app.models.ids import SpriteId
from app.plugins_factory import create_plugin
from defer import Defer
from resources import FileResource, HttpResource

import dupermechs.all as sm

plugin = create_plugin(__name__)


async def get_image_url(
    sprite_id: SpriteId, item: sm.IItem, files: abc.MutableSequence[File]
) -> str | None:
    if (url := gfx.get_image_url(sprite_id)) is not None:
        return url

    match await gfx.fetch_image(sprite_id):
        case Ok(image):
            url, file = embed_image(image, item.name)
            files.append(file)
            return url

        case Err(None):
            return None

        case Err(Exception() as error):
            plugin.logger.error("Failed to fetch sprite:", exc_info=error)

        case Err(error):
            plugin.logger.error("Failed to fetch sprite: %s", error)

    return None


def get_icon_url(item: sm.IItem, files: abc.MutableSequence[File]) -> str | None:
    match get_slot_icon(item.type):
        case FileResource() as icon_file:
            url, file = embed_file_resource(icon_file)
            files.append(file)
            return url

        case HttpResource(url):
            return str(url)

        case None:
            return None


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
    legacy: bool = False,
) -> None:
    """Lookup item stats. {{ ITEM }}

    Parameters
    ----------
    name:
        The name of the item. {{ ITEM_NAME }}
    type:
        Limit suggestions to this type. {{ ITEM_TYPE }}
    element:
        Limit suggestions to this element. {{ ITEM_ELEMENT }}
    rarity:
        Remove suggestions below this rarity. {{ ITEM_TIER }}
    legacy:
        Show legacy items. {{ ITEM_LEGACY }}
    """  # noqa: D400
    for item in packs.filter_items(type, element, rarity, legacy):
        if item.name == name:
            break

    else:
        msg = i18n.get_message(i18n.get_locale(inter), "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    files: list[File] = []
    icon_url = get_icon_url(item, files)

    from .item_lookup import ItemUIContext, get_embed_default, item_view

    ctx = ItemUIContext(
        item=item,
        locale=i18n.get_locale(inter),
        stage_index=len(item.stages) - 1,
        level_index=len(item.stages[-1].levels) - 1,
        icon_url=icon_url,
    )
    store = ui.callback_store(inter)
    layout = item_view(store, ctx)
    embed = get_embed_default(ctx)
    if __debug__:
        debug_message(embed, layout)
    await inter.response.send_message(embed=embed, files=files, components=layout, ephemeral=True)
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.user_input_timeout)


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def item_raw(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
    legacy: bool = False,
) -> None:
    """Lookup raw item stats.

    Parameters
    ----------
    name:
        The name of the item.
    type:
        Limit suggestions to this type.
    element:
        Limit suggestions to this element.
    rarity:
        Remove suggestions below this rarity.
    legacy:
        Show legacy items.
    """
    for item in packs.filter_items(type, element, rarity, legacy):
        if item.name == name:
            break

    else:
        msg = i18n.get_message(i18n.get_locale(inter), "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    await inter.response.send_message(f"`{item!r:.{MessageLimits.content - 2}}`", ephemeral=True)


def str_type(type: sm.Item.Type) -> str:
    return type.name.replace("_", " ").lower()


def str_elem(element: sm.Item.Element) -> str:
    return element.name.capitalize()


@plugin.slash_command()
async def compare(
    inter: CommandInteraction,
    item_a_name: str = commands.Param(name="item1", autocomplete=item_name_autocomplete),
    item_b_name: str = commands.Param(name="item2", autocomplete=item_name_autocomplete),
) -> None:
    """Interactive comparison between two items. {{ COMPARE }}

    Parameters
    ----------
    item_a_name:
        First item to compare. {{ COMPARE_FIRST }}
    item_b_name:
        Second item to compare. {{ COMPARE_SECOND }}
    """  # noqa: D400
    locale = i18n.get_locale(inter)
    item_a = None
    item_b = None

    match item_a, item_b:
        case None, None:
            msg = "Items not found."
            raise commands.UserInputError(msg)
        case None, _:  # pyright: ignore[reportUnnecessaryComparison]
            msg = "Item1 not found."
            raise commands.UserInputError(msg)
        case _, None:  # pyright: ignore[reportUnnecessaryComparison]
            msg = "Item2 not found."
            raise commands.UserInputError(msg)
        case _:
            pass

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
        color = COLORS.elements[item_a.element]

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    sikrit_footer(embed, locale)

    await inter.response.send_message(embed=embed, ephemeral=True)
    return  # FIXME

    from .item_lookup import item_compare_view

    store = ui.callback_store(inter)
    layout = item_compare_view(store, embed, item_a, item_b, locale)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.user_input_timeout)


setup, teardown = plugin.create_extension_handlers()
