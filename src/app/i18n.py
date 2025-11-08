import logging
import typing
from collections import abc
from pathlib import Path
from typing import Final, Literal, cast as type_cast

import attrs
import msgspec
from monads.option import Null, Option, Some

from app.disnake_types import HasLocale
from disnake import Locale, LocalizationProtocol

from app.class_utils import unset_to_option
from app.typeshed import Pathish

from dupermechs.enums import ItemRarity, ItemStat

__all__ = ("GetText", "get_gettext", "get_message", "get_stat_name", "load")

type LocalePair[KT] = tuple[KT, Locale]
type LiteralKey = Literal[
    "command-dev",
    "command-running",
    "command-timeout",
    "command-error",
    "unknown-item-name",
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
    "item-lookup-ui-level-select-label",
    "item-lookup-ui-select-placeholder",
    "item-lookup-ui-select-up-label",
    "item-lookup-ui-select-down-label",
    "item-lookup-jump-required",
    "item-lookup-no-stats",
    "item-lookup-no-image",
    "item-lookup-stats-header",
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

stats: Final[abc.Mapping[LocalePair[str], str]] = {}
messages: Final[abc.Mapping[LocalePair[LiteralKey], str]] = {}
locale_info: Final[abc.Mapping[Locale, "LocaleInfo"]] = {}
_command_locale: Final[abc.Mapping[str, dict[str, str]]] = {}
# provider only needs .get(_: str, /) -> Mapping[str, str] | None, which the above has
localization_provider: Final = type_cast("LocalizationProtocol", _command_locale)

locale_override: Option[Locale] = Null.null


def get_locale(inter: HasLocale, /) -> Locale:
    return locale_override.unwrap_or(inter.locale)


def set_locale_override(locale: Locale) -> None:
    global locale_override
    locale_override = Some(locale)


def remove_locale_override() -> None:
    global locale_override
    locale_override = Null.null


@attrs.define
class GetText:
    locale: Locale

    def __call__(self, key: LiteralKey, /, **format_kwargs: object) -> str:
        return get_message(self.locale, key, **format_kwargs)

    def get_stat_name(self, stat: ItemStat, /) -> str:
        return _get(stats, stat, self.locale)

    def get_tier_name(self, tier: ItemRarity, /) -> str:
        return get_message(self.locale, f"tier-{tier.name}")  # pyright: ignore[reportArgumentType]


def _get[KT](store: abc.MutableMapping[LocalePair[KT], str], key: KT, locale: Locale) -> str:
    try:
        return store[key, locale]

    except KeyError:
        try:
            value = store[key, FALLBACK_LOCALE]

        except KeyError:
            _LOG.error("Key %s does not exist", key)
            value = str(key)
            store[key, FALLBACK_LOCALE] = value

        else:
            _LOG.warning("Locale %s has no key %r", locale, key)
            store[key, locale] = value

        return value


def get_stat_name(locale: Locale, stat: ItemStat) -> str:
    return _get(stats, stat, locale)


def get_message(locale: Locale, key: LiteralKey, /, **format_kwargs: object) -> str:
    msg = _get(messages, key, locale)

    if format_kwargs:
        return msg.format_map(format_kwargs)

    return msg


def get_gettext(locale: Locale, /) -> GetText:
    return GetText(locale)


class _LocaleMeta(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: str | msgspec.UnsetType = msgspec.UNSET
    region: str | msgspec.UnsetType = msgspec.UNSET


class _LocaleData(msgspec.Struct):
    meta: _LocaleMeta
    stats: abc.Mapping[str, str]
    messages: abc.Mapping[LiteralKey, str] | msgspec.UnsetType = msgspec.UNSET
    commands: dict[str, str] | msgspec.UnsetType = msgspec.UNSET


class LocaleInfo(msgspec.Struct):
    english_name: str
    local_name: str
    flag_emoji: Option[str] = Null.null
    region: Option[str] = Null.null


def _load_locale_file(path: Path, /) -> None:
    if not path.is_file():
        msg = f"Path {path} is not a file"
        raise FileNotFoundError(msg)

    locale = Locale[path.stem]
    _LOG.info("Loading locale for %s", locale)
    data = msgspec.toml.decode(path.read_bytes(), type=_LocaleData)

    for key, entry in data.stats.items():
        stat = ItemStat[key]
        stats[stat, locale] = entry

    if data.messages is not msgspec.UNSET:
        for key, message in data.messages.items():
            messages[key, locale] = message

    if data.commands is not msgspec.UNSET:
        _command_locale[locale.value] = data.commands

    locale_info[locale] = LocaleInfo(
        english_name=data.meta.english_name,
        local_name=data.meta.local_name,
        flag_emoji=unset_to_option(data.meta.flag_emoji),
        region=unset_to_option(data.meta.region),
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
                    stats[stat, locale]

                except KeyError:
                    missing.append(stat.name)

            for key in typing.get_args(LiteralKey.__value__):
                try:
                    messages[key, locale]

                except KeyError:
                    missing.append(key)

            if missing:
                print(f"{locale} is missing: {', '.join(missing)}")

    test_stat_locales()
