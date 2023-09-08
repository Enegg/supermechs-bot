from disnake import CommandInteraction
from disnake.ext import commands

from managers import item_pack_manager, player_manager

from .autocompleters import item_name_autocomplete

from supermechs.api import ItemData, Player
from supermechs.typedefs import Name

__all__ = ("register_injections",)


def register_injections() -> None:
    """Entry point for registering all injections for the commands module."""
    # NOTE: this function exists purely so as not to have the injectors
    # being registered as a *side effect* of importing this module (as otherwise
    # somewhere in the main.py we'd need a blank import which isn't used anywhere)

    @commands.register_injection
    def item_injector(inter: CommandInteraction, name: Name) -> ItemData:
        """Injection taking Item name and returning the Item.

        Parameters
        ----------
        name: The name of the item. {{ ITEM_NAME }}
        """
        # TODO: make this pack-aware
        del inter
        default_pack = item_pack_manager["@Darkstare"]  # TODO
        try:
            return default_pack.get_item_by_name(name)

        except KeyError as err:
            raise commands.UserInputError("Item not found.") from err

    @commands.register_injection
    def player_injector(inter: CommandInteraction) -> Player:
        return player_manager(inter.author)

    item_injector.autocomplete("name")(item_name_autocomplete)
    del player_injector
