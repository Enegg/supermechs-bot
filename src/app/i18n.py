import logging
import typing
from collections import abc
from pathlib import Path
from typing import Literal, Protocol

import attrs
import msgspec

from disnake import Locale

from app.core import AppState
from app.core.state import LocaleInfo
from app.typeshed import Pathish
from app.utils import unset_to_option

from supermechs.enums import ItemRarity, ItemStat

__all__ = ("GetText", "Locale", "get_gettext", "get_message", "load")

type LocalePair[KT] = tuple[KT, Locale]
type LiteralKey = Literal[
    "command-dev",
    "command-running",
    "command-timeout",
    "command-error",
    "unknown-item-name",  # {name}
    # ui
    "ui-disallowed",
    "ui-quit",
    "ui-empty-option-label",
    "ui-empty-option-desc",
    "ui-cmd-cancel-button",
    # item-lookup
    "item-lookup-ui-buffs",
    "item-lookup-ui-damage-avg",
    "item-lookup-ui-damage-vs-titans",
    "item-lookup-power-level",
    "item-lookup-power-required",
    "item-lookup-ui-level-select-label",  # {level}
    "item-lookup-ui-level-select-placeholder",
    "item-lookup-ui-tier-select-placeholder",
    "item-lookup-ui-select-next-label",  # {min}, {max}
    "item-lookup-jump-required",
    "item-lookup-no-stats",
    "item-lookup-no-image",
    "item-lookup-stats-header",
    "item-lookup-item-not-available",  # {command}
    "item-lookup-item-changed-info",  # {command}
    # item-compare
    "item-compare-ui-buffs",
    "item-compare-jump-required",
    "item-compare-stat-header",
    # tiers
    "tier-common",
    "tier-rare",
    "tier-epic",
    "tier-legendary",
    "tier-mythical",
    "tier-divine",
    "tier-perk",
    # other
    "boost-power",
]

_LOG = logging.getLogger(__name__)
FALLBACK_LOCALE = Locale.en_US
FILE_EXT = ".toml"


class HasLocale(Protocol):
    @property
    def locale(self) -> Locale: ...


@attrs.define
class GetText:
    locale: Locale

    def __call__(self, key: LiteralKey, /, **format_kwargs: object) -> str:
        return get_message(self.locale, key, **format_kwargs)

    def get_stat_name(self, stat: ItemStat, /) -> str:
        return _get(AppState.I18n.stats, stat, self.locale)

    def get_tier_name(self, tier: ItemRarity, /) -> str:
        return get_message(self.locale, "tier-" + tier.name)


def _get[KT](mapping: abc.MutableMapping[LocalePair[KT], str], key: KT, locale: Locale) -> str:
    try:
        return mapping[key, locale]

    except KeyError:
        try:
            value = mapping[key, FALLBACK_LOCALE]

        except KeyError:
            _LOG.error("Key %s does not exist", key)
            value = mapping[key, locale] = mapping[key, FALLBACK_LOCALE] = str(key)

        else:
            _LOG.warning("Locale %s has no key %r", locale, key)
            mapping[key, locale] = value

        return value


def get_message(locale: Locale, key: LiteralKey, /, **format_kwargs: object) -> str:
    msg = _get(AppState.I18n.messages, key, locale)

    if format_kwargs:
        return msg.format_map(format_kwargs)

    return msg


def get_gettext(inter: HasLocale, /) -> GetText:
    return GetText(AppState.I18n.locale_override.unwrap_or(inter.locale))


class _LocaleMetadata(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: str | msgspec.UnsetType = msgspec.UNSET
    region: str | msgspec.UnsetType = msgspec.UNSET


class _LocaleFileStruct(msgspec.Struct):
    metadata: _LocaleMetadata
    stats: abc.Mapping[str, str]
    messages: abc.Mapping[LiteralKey, str] | msgspec.UnsetType = msgspec.UNSET
    commands: dict[str, str] | msgspec.UnsetType = msgspec.UNSET


def _load_locale_file(path: Path, /) -> None:
    # precondition: path.suffix equals FILE_EXT

    locale = Locale[path.stem]
    _LOG.info("Loading locale for %s", locale)
    data = msgspec.toml.decode(path.read_bytes(), type=_LocaleFileStruct)

    for key, entry in data.stats.items():
        stat = ItemStat[key]
        AppState.I18n.stats[stat, locale] = entry

    if data.messages is not msgspec.UNSET:
        for key, message in data.messages.items():
            AppState.I18n.messages[key, locale] = message

    if data.commands is not msgspec.UNSET:
        AppState.I18n.command_locale[locale.value] = data.commands

    AppState.I18n.locale_info[locale] = LocaleInfo(
        english_name=data.metadata.english_name,
        local_name=data.metadata.local_name,
        flag_emoji=unset_to_option(data.metadata.flag_emoji),
        region=unset_to_option(data.metadata.region),
    )


def load(directory: Pathish, /) -> None:
    for subpath in Path(directory).glob(f"*{FILE_EXT}"):
        try:
            _load_locale_file(subpath)

        except Exception as exc:
            _LOG.error("Failed to load locale:", exc_info=exc)


if __name__ == "__main__":

    def test_stat_locales() -> None:
        from app import paths  # noqa: PLC0415

        load(paths.LOCALE_DIR)

        for file_path in paths.LOCALE_DIR.glob(f"*{FILE_EXT}"):
            locale = Locale[file_path.stem]
            missing: list[str] = []

            for stat in ItemStat:
                if stat.name.endswith("addon"):
                    continue

                try:
                    AppState.I18n.stats[stat, locale]

                except KeyError:
                    missing.append(stat.name)

            for key in typing.get_args(LiteralKey.__value__):
                try:
                    AppState.I18n.messages[key, locale]

                except KeyError:
                    missing.append(key)

            if missing:
                print(f"{locale} is missing: {', '.join(missing)}")

    test_stat_locales()
