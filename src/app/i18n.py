import logging
from collections import abc
from functools import partial
from pathlib import Path
from typing import Final, NotRequired, Protocol, ReadOnly, Required, TypedDict, cast as type_cast

import rtoml
from monads.option import Null, Option, Some

from disnake import Locale, LocalizationProtocol

from app.typeshed import Pathish

from supermechs.enums import StatName

__all__ = ("GetText", "get_embed_tips", "get_gettext", "get_message", "get_stat_name", "load")

type LocalePair[KT] = tuple[KT, Locale]


class GetText(Protocol):
    def __call__(self, key: str, /, **format_kwargs: object) -> str: ...


_LOGGER = logging.getLogger(__name__)
FALLBACK_LOCALE = Locale.en_US
FALLBACK_NAME = "???"
FILE_EXT = ".toml"

stats: Final[abc.Mapping[LocalePair[str], str]] = {}
messages: Final[abc.Mapping[LocalePair[str], str]] = {}
embed_tips: Final[abc.Mapping[Locale, abc.Sequence[str]]] = {}
_command_locale: Final[abc.Mapping[str, dict[str, str]]] = {}
# provider only needs .get(_: str, /) -> Mapping[str, str] | None, which the above has
localization_provider: Final = type_cast("LocalizationProtocol", _command_locale)

locale_override: Option[Locale] = Null.null


def set_locale_override(locale: Locale) -> None:
    global locale_override
    locale_override = Some(locale)


def remove_locale_override() -> None:
    global locale_override
    locale_override = Null.null


def _get[KT](
    store: abc.MutableMapping[LocalePair[KT], str],
    key: KT,
    locale: Locale,
    default: str | None = None,
) -> str:
    try:
        return store[key, locale]

    except KeyError:
        try:
            value = store[key, FALLBACK_LOCALE]

        except KeyError:
            _LOGGER.error("Key %s does not exist.", key)  # noqa: TRY400
            value = str(key) if default is None else default

        else:
            _LOGGER.warning("Key %s does not exist for locale %s.", key, locale)
            # prevent further logs
            store[key, locale] = value

        return value


def get_stat_name(locale: Locale, stat: str) -> str:
    return _get(stats, stat, locale, default=FALLBACK_NAME)


def get_message(locale: Locale, key: str, /, **format_kwargs: object) -> str:
    msg = _get(messages, key, locale)

    if format_kwargs:
        return msg.format_map(format_kwargs)

    return msg


def get_gettext(locale: Locale, /) -> GetText:
    return partial(get_message, locale)


def get_embed_tips(locale: Locale, /) -> abc.Sequence[str]:
    try:
        return embed_tips[locale]

    except KeyError as err:
        try:
            return embed_tips[FALLBACK_LOCALE]

        except KeyError:
            raise err from None


class _StatEntry(TypedDict):
    in_game: ReadOnly[str]
    default: ReadOnly[NotRequired[str]]
    short: ReadOnly[NotRequired[str]]


class _LocaleData(TypedDict, total=False):
    stats: ReadOnly[Required[abc.Mapping[str, _StatEntry]]]
    messages: ReadOnly[abc.Mapping[str, str]]
    commands: ReadOnly[dict[str, str]]
    embed_tips: ReadOnly[abc.Sequence[str]]


def _load_file(path: Path, /) -> None:
    if not path.is_file():
        msg = f"Path {path} is not a file"
        raise FileNotFoundError(msg)

    locale = Locale[path.stem]
    _LOGGER.info("Loading locale for %s", locale)
    data = type_cast("_LocaleData", rtoml.loads(path.read_text("utf-8")))

    for key, entry in data["stats"].items():
        stat = StatName[key]
        stats[stat, locale] = entry.get("default") or entry.get("in_game", FALLBACK_NAME)

    if messages_data := data.get("messages"):
        for key, message in messages_data.items():
            messages[key, locale] = message

    if commands_data := data.get("commands"):
        _command_locale[locale.value] = commands_data

    if tips_data := data.get("embed_tips"):
        embed_tips[locale] = tuple(tips_data)


def load(directory: Pathish, /) -> None:
    for subpath in Path(directory).glob(f"*{FILE_EXT}"):
        _load_file(subpath)


if __name__ == "__main__":

    def test_stat_locales() -> None:
        from app import paths

        locale_path = paths.LOCALE_DIR
        load(locale_path)

        for file_path in locale_path.glob(f"*{FILE_EXT}"):
            locale = Locale[file_path.stem]

            for stat in StatName:
                if stat.name.endswith("addon"):
                    continue

                try:
                    name = stats[stat, locale]

                except KeyError:
                    print(f"{stat.name} for {locale} is missing")

                else:
                    if name == FALLBACK_NAME:
                        print(f"{stat.name} for {locale} is {FALLBACK_NAME}")

    test_stat_locales()
