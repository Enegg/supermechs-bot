import disnake
from disnake import CommandInteraction
from disnake.ext import commands

import i18n
from env import ENV
from models import Player
from shared.item_packs import get_item_by_name, get_item_pack_for
from stored import players

from .autocompleters import item_name_autocomplete

from supermechs.abc.item import Name
from supermechs.api import ItemData

__all__ = ("register_injections",)


def register_injections() -> None:
    """Entry point for registering all injections for the commands module."""
    # NOTE: this function exists purely so as not to have the injectors
    # being registered as a *side effect* of importing this module (as otherwise
    # somewhere in the main.py we'd need a blank import which isn't used anywhere)

    @commands.register_injection
    def inject_item(inter: CommandInteraction, name: Name, locale: disnake.Locale) -> ItemData:
        """Injection taking Item name and returning ItemData.

        Parameters
        ----------
        name: The name of the item. {{ ITEM_NAME }}
        """
        item_pack = get_item_pack_for(inter)
        item = get_item_by_name(item_pack.items, name)
        if item is not None:
            return item

        msg = i18n.get_message(locale, "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    @commands.register_injection
    def inject_player(inter: CommandInteraction) -> Player:
        """Injection creating a player from interaction."""
        return players(inter.author)

    @commands.register_injection
    def inject_locale(inter: CommandInteraction) -> disnake.Locale:
        """Injection returning context aware locale."""
        return ENV.locale_override or inter.locale

    @commands.register_injection
    def inject_gettext(inter: CommandInteraction) -> i18n.GetText:
        """Injection returning a callable which returns localized messages."""
        return i18n.get_gettext(ENV.locale_override or inter.locale)

    inject_item.autocomplete("name")(item_name_autocomplete)
    del inject_player, inject_gettext, inject_locale
