from __future__ import annotations

import typing as t

from disnake import CommandInteraction, Embed, File
from disnake.ext import commands, plugins

from config import TEST_GUILDS
from library_extensions import sanitize_filename

from .item_lookup import ItemCompareView, ItemView, compact_fields, default_fields

from SuperMechs.enums import Element, Type
from SuperMechs.images import image_to_fp
from SuperMechs.item import AnyItem
from SuperMechs.typedefs import LiteralElement, LiteralType, Name
from SuperMechs.utils import search_for

if t.TYPE_CHECKING:
    from bot import SMBot

    LiteralTypeOrAny = LiteralType | t.Literal["ANY"]
    LiteralElementOrAny = LiteralElement | t.Literal["ANY"]

else:
    # disnake cannot parse unions of literals
    LiteralTypeOrAny = t.Literal[t.get_args(LiteralType) + ("ANY",)]
    LiteralElementOrAny = t.Literal[t.get_args(LiteralElement) + ("ANY",)]


plugin = plugins.Plugin["SMBot"](name="Item-lookup")


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    name: Name,
    type: LiteralTypeOrAny = "ANY",
    element: LiteralElementOrAny = "ANY",
    compact: bool = False,
) -> None:
    """Finds an item and returns its stats {{ ITEM }}

    Parameters
    -----------
    name: The name of the item {{ ITEM_NAME }}
    type: If provided, filters suggested names to given type. {{ ITEM_TYPE }}
    element: If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    compact: Whether the embed sent back should be compact (breaks on mobile) {{ ITEM_COMPACT }}
    """

    if name not in plugin.bot.default_pack:
        raise commands.UserInputError("Item not found.")

    item = plugin.bot.default_pack.get_item_by_name(name)

    fp = image_to_fp(item.image.image)
    file = File(fp, sanitize_filename(item.name, ".png"))
    url = f"attachment://{file.filename}"

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
    name: Name,
    type: LiteralTypeOrAny = "ANY",
    element: LiteralElementOrAny = "ANY",
) -> None:
    """Finds an item and returns its raw stats {{ ITEM }}

    Parameters
    -----------
    name: The name of the item or an abbreviation of it {{ ITEM_NAME }}
    type: If provided, filters suggested names to given type. {{ ITEM_TYPE }}
    element: If provided, filters suggested names to given element. {{ ITEM_ELEMENT }}
    """

    if name not in plugin.bot.default_pack.names_to_ids:
        if name == "Start typing to get suggestions...":
            raise commands.UserInputError("This is only an information and not an option")

        raise commands.UserInputError("Item not found.")

    item = plugin.bot.default_pack.get_item_by_name(name)

    await inter.response.send_message(f"`{item!r}`", ephemeral=True)


@plugin.slash_command()
async def compare(inter: CommandInteraction, item1: Name, item2: Name) -> None:
    """Shows an interactive comparison of two items. {{ COMPARE }}

    Parameters
    -----------
    item1: First item to compare. {{ COMPARE_FIRST }}
    item2: Second item to compare. {{ COMPARE_SECOND }}
    """

    try:
        item_a = plugin.bot.default_pack.get_item_by_name(item1)
        item_b = plugin.bot.default_pack.get_item_by_name(item2)

    except KeyError as e:
        raise commands.UserInputError(*e.args) from e

    def str_type(type: Type) -> str:
        return type.name.replace("_", " ").lower()

    def str_elem(element: Element) -> str:
        return element.name.capitalize()

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


@item.autocomplete("name")
@item_raw.autocomplete("name")
@compare.autocomplete("item1")
@compare.autocomplete("item2")
async def item_autocomplete(inter: CommandInteraction, input: str) -> list[Name]:
    """Autocomplete for items with regard for type & element."""
    OPTION_LIMIT = 25

    pack = plugin.bot.default_pack
    filters: list[t.Callable[[AnyItem], bool]] = []

    if (type_name := inter.filled_options.get("type", "ANY")) != "ANY":
        filters.append(lambda item: item.type is Type[type_name])

    if (element_name := inter.filled_options.get("element", "ANY")) != "ANY":
        filters.append(lambda item: item.element is Element[element_name])

    abbrevs = pack.name_abbrevs.get(input.lower(), set())

    def filter_item_names(names: t.Iterable[Name]) -> t.Iterator[Name]:
        items = map(pack.get_item_by_name, names)
        filtered_items = (item for item in items if all(func(item) for func in filters))
        return (item.name for item in filtered_items)

    # place matching abbreviations at the top
    matching_item_names = sorted(filter_item_names(abbrevs))

    # this shouldn't ever happen, but handle it anyway
    if len(matching_item_names) >= OPTION_LIMIT:
        del matching_item_names[OPTION_LIMIT:]
        return matching_item_names

    import heapq

    # extra filter to exclude duplicates
    filters.append(lambda item: item.name not in abbrevs)

    # extend names up to 25
    matching_item_names += heapq.nsmallest(
        OPTION_LIMIT - len(matching_item_names),
        filter_item_names(search_for(input, pack.iter_item_names())),
    )
    return matching_item_names


setup, teardown = plugin.create_extension_handlers()
