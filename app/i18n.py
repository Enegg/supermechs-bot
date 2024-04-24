import logging
import typing
import typing_extensions as typing_
from collections import abc
from pathlib import Path

import rtoml
from disnake import Locale, LocalizationProtocol

from typeshed import KT, VT, Pathish

from supermechs.enums.stats import Stat

__all__ = ("load", "stats", "messages", "get_stat_name", "get_message")

LocalePair: typing.TypeAlias = tuple[KT, Locale]
GetText: typing.TypeAlias = abc.Callable[[str], str]

_LOGGER = logging.getLogger(__name__)
FALLBACK_LOCALE = Locale.en_US
FALLBACK_NAME = "???"
FILE_EXT = ".toml"

stats: typing.Final[abc.Mapping[LocalePair[Stat], "StatName"]] = {}
messages: typing.Final[abc.Mapping[LocalePair[str], str]] = {}
_command_locale: typing.Final[abc.Mapping[str, dict[str, str]]] = {}
# provider only needs .get(_: str, /) -> Mapping[str, str] | None, which the above has
localization_provider: typing.Final = typing.cast(LocalizationProtocol, _command_locale)


def get(
    store: abc.Mapping[LocalePair[KT], VT], pair: LocalePair[KT], default: VT | None = None
) -> VT:
    try:
        value = store[pair]

    except KeyError as err:
        try:
            value = store[pair[0], FALLBACK_LOCALE]

        except KeyError:
            if default is None:
                raise err from None

            value = default

    return value


def get_stat_name(locale: Locale, stat: Stat, /) -> "StatName":
    return get(stats, (stat, locale), default=_MISSING_STAT)


def get_message(locale: Locale, key: str, /) -> str:
    return get(messages, (key, locale))


class _StatEntry(typing.TypedDict):
    in_game: str
    default: typing_.NotRequired[str]
    short: typing_.NotRequired[str]


class StatName(typing.NamedTuple):
    in_game: str
    default_: str | None
    short_: str | None

    @property
    def default(self) -> str:
        return self.default_ or self.in_game

    @property
    def short(self) -> str:
        return self.short_ or min(self.default, self.in_game, key=len)

    def __str__(self) -> str:
        return self.default


_MISSING_STAT = StatName(FALLBACK_NAME, None, None)


def _load_stats(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    stats_data: abc.Mapping[str, _StatEntry] = data["stats"]

    for key, entry in stats_data.items():
        stat = Stat[key]
        stat_name = StatName(
            entry.get("in_game", FALLBACK_NAME),
            entry.get("default"),
            entry.get("short"),
        )
        stats[stat, locale] = stat_name


def _load_messages(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    messages_data: abc.Mapping[str, str] = data.get("messages") or {}

    for key, message in messages_data.items():
        messages[key, locale] = message


def _load_commands(data: abc.Mapping[str, typing.Any], /, locale: Locale) -> None:
    commands_data: dict[str, str] | None = data.get("commands")

    if commands_data:
        _command_locale[locale.value] = commands_data


def _load_file(path: Path, /) -> None:
    locale = Locale[path.stem]
    _LOGGER.info("Loading locale for %s", locale)
    data = rtoml.loads(path.read_text("utf-8"))

    for loader in (_load_stats, _load_messages, _load_commands):
        loader(data, locale)


def _walk_files(directory: Pathish, /, ext: str) -> abc.Iterator[Path]:
    path = Path(directory)

    if not ext.startswith("."):
        ext = "." + ext

    if path.is_file():
        if path.suffix != ext:
            msg = f"Not a {ext} file"
            raise ValueError(msg)
        yield path

    elif path.is_dir():
        for subpath in path.glob(f"*{ext}"):
            if subpath.is_file():
                yield subpath

            else:
                msg = f"Path {subpath} is not a file"
                raise FileNotFoundError(msg)

    else:
        msg = f"Path {path} is not a directory / file"
        raise RuntimeError(msg)


def load(directory: Pathish, /) -> None:
    path = Path(directory)

    for subpath in _walk_files(path, FILE_EXT):
        _load_file(subpath)


if __name__ == "__main__":

    def test_stat_locales():
        locale_path = Path.cwd() / "locale"
        load(locale_path)

        for file_path in _walk_files(locale_path, FILE_EXT):
            locale = Locale[file_path.stem]

            for stat in Stat:
                try:
                    name = stats[stat, locale]

                except KeyError:
                    print(f"{stat} for {locale=} is missing")

                else:
                    if name.in_game == FALLBACK_NAME:
                        print(f"{stat} for {locale=} is missing in_game name")

    test_stat_locales()
