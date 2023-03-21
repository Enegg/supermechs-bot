from disnake.ext import commands

from library_extensions import CommandInteraction

from .autocompleters import item_name_autocomplete

from SuperMechs.client import SMClient
from SuperMechs.item import Item
from SuperMechs.player import Player
from SuperMechs.typedefs import Name

__all__ = ("register_injections",)


def item_injector(inter: CommandInteraction[SMClient], name: Name) -> Item:
    """Injection taking Item name and returning the Item.

    Parameters
    ----------
    name: The name of the item. {{ ITEM_NAME }}
    """
    # TODO: make this pack-aware
    try:
        return inter.bot.app.default_pack.get_item_by_name(name)

    except KeyError as err:
        raise commands.UserInputError("Item not found.") from err


def player_injector(inter: CommandInteraction[SMClient]) -> Player:
    return inter.bot.app.state.store_player(inter.author)


def register_injections() -> None:
    """Entry point for registering all injections for the commands module."""
    # @commands.register_injection
    # def player_injector(inter: CommandInteraction) -> Player:
    #     return get_player(inter)
    commands.register_injection(player_injector)
    commands.register_injection(item_injector, autocompleters={"name": item_name_autocomplete})

    # item_injector.autocomplete("name")(item_name_autocomplete)
