import logging
from collections import abc
from typing import Protocol

import attrs

from disnake import Locale

from app import const, structs
from app.core.state import I18nStore, State

from supermechs.enums import ItemRarity, ItemStat

__all__ = ("GetText", "get_gettext", "get_message")


_LOG = logging.getLogger(__name__)


class HasLocale(Protocol):
    @property
    def locale(self) -> Locale: ...


@attrs.define
class GetText:
    locale: Locale
    store: I18nStore

    def __call__(self, key: structs.I18nKey, /, **format_kwargs: object) -> str:
        return get_message(self.store, self.locale, key, **format_kwargs)

    def get_stat_name(self, stat: ItemStat, /) -> str:
        return _get(self.store.stat_l10ns, stat, self.locale)

    def get_tier_name(self, tier: ItemRarity, /) -> str:
        return get_message(self.store, self.locale, "tier-" + tier.name)


def _get[KT](
    mapping: abc.MutableMapping[structs.LocalePair[KT], str], key: KT, locale: Locale
) -> str:
    try:
        return mapping[key, locale]

    except KeyError:
        try:
            value = mapping[key, const.FALLBACK_LOCALE]

        except KeyError:
            _LOG.error("Key %r does not exist", key)
            value = mapping[key, locale] = mapping[key, const.FALLBACK_LOCALE] = str(key)

        else:
            _LOG.warning("Locale %s has no key %r", locale, key)
            mapping[key, locale] = value

        return value


def get_message(
    store: I18nStore, locale: Locale, key: structs.I18nKey, /, **format_kwargs: object
) -> str:
    msg = _get(store.message_l10ns, key, locale)

    if format_kwargs:
        return msg.format_map(format_kwargs)

    return msg


def get_gettext(inter: HasLocale, /, state: State) -> GetText:
    return GetText(
        inter.locale if state.debug.locale_override is None else state.debug.locale_override,
        state.i18n,
    )
