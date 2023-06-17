from disnake import CommandInteraction
from disnake.ext import commands

from .autocompleters import item_name_autocomplete
from .context import AppContext

from supermechs.api import Item, Player, SMClient
from supermechs.typedefs import Name

__all__ = ("register_injections",)


def register_injections(client: SMClient) -> None:
    """Entry point for registering all injections for the commands module."""

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
        return client.state.store_player(inter.author)

    @commands.register_injection
    def context_injector(inter: CommandInteraction) -> AppContext:
        return AppContext(client, inter)

    item_injector.autocomplete("name")(item_name_autocomplete)
    del player_injector, context_injector
