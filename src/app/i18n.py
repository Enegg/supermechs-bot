import logging
import typing
import typing_extensions as typing_
from collections import abc
from functools import partial
from pathlib import Path

import rtoml

from app.typeshed import KT, Pathish

from disnake import Locale, LocalizationProtocol

from supermechs.enums.stats import Stat

__all__ = ("GetText", "get_embed_tips", "get_gettext", "get_message", "get_stat_name", "load")

LocalePair: typing.TypeAlias = tuple[KT, Locale]


class GetText(typing.Protocol):
    def __call__(self, key: str, /, **format_kwargs: object) -> str: ...


_LOGGER = logging.getLogger(__name__)
FALLBACK_LOCALE = Locale.en_US
FALLBACK_NAME = "???"
FILE_EXT = ".toml"

stats: typing.Final[abc.Mapping[LocalePair[Stat], str]] = {}
messages: typing.Final[abc.Mapping[LocalePair[str], str]] = {}
embed_tips: typing.Final[abc.Mapping[Locale, abc.Sequence[str]]] = {}
_command_locale: typing.Final[abc.Mapping[str, dict[str, str]]] = {}
# provider only needs .get(_: str, /) -> Mapping[str, str] | None, which the above has
localization_provider: typing.Final = typing.cast(LocalizationProtocol, _command_locale)


def _get(
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


def get_stat_name(locale: Locale, stat: Stat) -> str:
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


class _StatEntry(typing.TypedDict):
    in_game: str
    default: typing_.NotRequired[str]
    short: typing_.NotRequired[str]


def _load_stats(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    stats_data: abc.Mapping[str, _StatEntry] = data["stats"]

    for key, entry in stats_data.items():
        stat = Stat[key]
        name = entry.get("default") or entry.get("in_game", FALLBACK_NAME)
        stats[stat, locale] = name


def _load_messages(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    messages_data: abc.Mapping[str, str] = data.get("messages") or {}

    for key, message in messages_data.items():
        messages[key, locale] = message


def _load_commands(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    commands_data: dict[str, str] | None = data.get("commands")

    if commands_data:
        _command_locale[locale.value] = commands_data


def _load_tips(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    tips_data: abc.Sequence[str] | None = data.get("embed_tips")

    if tips_data is not None:
        embed_tips[locale] = tuple(tips_data)


def _load_file(path: Path, /) -> None:
    if not path.is_file():
        msg = f"Path {path} is not a file"
        raise FileNotFoundError(msg)

    locale = Locale[path.stem]
    _LOGGER.info("Loading locale for %s", locale)
    data = rtoml.loads(path.read_text("utf-8"))

    for loader in (_load_stats, _load_messages, _load_commands, _load_tips):
        loader(data, locale)


def load(directory: Pathish, /) -> None:
    for subpath in Path(directory).glob(f"*{FILE_EXT}"):
        _load_file(subpath)


if __name__ == "__main__":

    def test_stat_locales() -> None:
        locale_path = Path.cwd() / "locale"
        load(locale_path)

        for file_path in locale_path.glob(f"*{FILE_EXT}"):
            locale = Locale[file_path.stem]

            for stat in Stat:
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
