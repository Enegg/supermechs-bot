import disnake
from app.disnake_types import CommandInteraction
from disnake.ext import commands

from app import i18n, state
from app.bridges.sm_utils import get_item_by_name, get_item_pack_for
from app.models import Player

from .autocompleters import item_name_autocomplete

from supermechs.all import ItemData

__all__ = ("register_injections",)

# NOTE: disnake does not accept pos-only params


def _inject_locale(inter: CommandInteraction) -> disnake.Locale:
    return i18n.locale_override.unwrap_or(inter.locale)


def _inject_item(inter: CommandInteraction, name: str) -> ItemData:
    """Injection taking Item name and returning ItemData.

    Parameters
    ----------
    name: The name of the item. {{ ITEM_NAME }}
    """
    item_pack = get_item_pack_for(inter)
    item = get_item_by_name(item_pack.items.values(), name=name)
    if item is not None:
        return item

    locale = _inject_locale(inter)
    msg = i18n.get_message(locale, "unknown-item-name", name=name)
    raise commands.UserInputError(msg)


def _inject_gettext(inter: CommandInteraction) -> i18n.GetText:
    return i18n.get_gettext(_inject_locale(inter))


def _inject_player(inter: CommandInteraction) -> Player:
    return state.players(inter.author)


def register_injections() -> None:
    """Entry point for registering all injections for the commands module."""
    # NOTE: this function exists purely so as not to have the injectors
    # being registered as a *side effect* of importing this module (as otherwise
    # somewhere in the main.py we'd need a blank import which isn't used anywhere)

    commands.register_injection(get_item_pack_for)
    commands.register_injection(_inject_locale)
    commands.register_injection(_inject_gettext)
    commands.register_injection(_inject_player)
    commands.register_injection(
        _inject_item,
    ).autocomplete("name")(item_name_autocomplete)
