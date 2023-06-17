from disnake import CommandInteraction
from disnake.ext import commands

from manager import player_manager

from .autocompleters import item_name_autocomplete
from .context import AppContext

from supermechs.api import Item, Player, SMClient
from supermechs.typedefs import Name

__all__ = ("register_injections",)


def register_injections(client: SMClient) -> None:
    """Entry point for registering all injections for the commands module."""
    # NOTE: this function exists purely so as not to have the injectors
    # being registered as a *side effect* of importing this module (as otherwise
    # somewhere in the main.py we'd need a blank import which isn't used anywhere)

    @commands.register_injection
    def item_injector(inter: CommandInteraction, name: Name) -> Item:
        """Injection taking Item name and returning the Item.

        Parameters
        ----------
        name: The name of the item. {{ ITEM_NAME }}
        """
        # TODO: make this pack-aware
        del inter
        try:
            return client.default_pack.get_item_by_name(name)

        except KeyError as err:
            raise commands.UserInputError("Item not found.") from err

    @commands.register_injection
    def player_injector(inter: CommandInteraction) -> Player:
        return player_manager.lookup_or_create(inter.author)

    @commands.register_injection
    def context_injector(inter: CommandInteraction) -> AppContext:
        return AppContext(client, inter)

    item_injector.autocomplete("name")(item_name_autocomplete)
    del player_injector, context_injector
