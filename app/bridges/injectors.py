from functools import partial

from disnake import CommandInteraction
from disnake.ext import commands

import i18n
from config import DEFAULT_PACK_KEY
from managers import item_pack_manager, player_manager

from .autocompleters import item_name_autocomplete
from .player import Player

from supermechs.abc.item import Name
from supermechs.api import ItemData

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
        default_pack = item_pack_manager[DEFAULT_PACK_KEY]
        try:
            return default_pack.get_item_by_name(name)

        except KeyError as err:
            raise commands.UserInputError("Item not found.") from err

    @commands.register_injection
    def player_injector(inter: CommandInteraction) -> Player:
        return player_manager(inter.author)

    @commands.register_injection
    def l10n_injector(inter: CommandInteraction) -> i18n.L10nGetter:
        """Injection returning a callable which returns localized messages."""
        return partial(i18n.get_message, inter.locale)

    item_injector.autocomplete("name")(item_name_autocomplete)
    del player_injector, l10n_injector
