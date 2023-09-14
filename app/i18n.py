import logging
import os
import typing as t
import typing_extensions as tex
from pathlib import Path

from disnake import Locale

from supermechs.item_stats import AnyStatKey
from supermechs.platform import toml_decoder

_LOGGER = logging.getLogger(__name__)


class _StatEntry(t.TypedDict):
    in_game: str
    default: tex.NotRequired[str]
    short: tex.NotRequired[str]


class _I18nFile(t.TypedDict):
    stats: t.Mapping[AnyStatKey, _StatEntry]


class StatName(t.NamedTuple):
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


LocaleEntry = dict[str, StatName]

loc = dict[Locale, LocaleEntry]()


def _load_file(path: Path, /) -> None:
    if path.suffix != ".toml":
        raise ValueError("Not a .toml file")

    locale = Locale[path.stem]
    _LOGGER.info("Loading locale for %s", locale)
    data: _I18nFile = toml_decoder(path.read_text("utf-8"))

    try:
        loc[locale] = {
            key: StatName(entry["in_game"], entry.get("default"), entry.get("short"))
            for key, entry in data["stats"].items()
        }
    except KeyError as err:
        if locale is Locale.en_US:
            raise RuntimeError("Locale key not found for en_US") from err

        _LOGGER.warning("Localization file for %s is missing a required key", locale, exc_info=err)


def load(directory: str | os.PathLike[str], /) -> None:
    path = Path(directory)
    suffix = ".toml"

    if path.is_file():
        if path.suffix != suffix:
            raise ValueError(f"Not a {suffix} file")
        _load_file(path)

    elif path.is_dir():
        for subpath in path.glob(f"*{suffix}"):
            if not subpath.is_file():
                continue

            _load_file(subpath)

    else:
        raise RuntimeError(f"Path {path} is not a directory / file")

    if Locale.en_US not in loc:
        raise RuntimeError("en_US locale was not loaded")


@t.overload
def get(locale: Locale, /) -> LocaleEntry:
    ...

@t.overload
def get(locale: Locale, /, key: str) -> StatName:
    ...

def get(locale: Locale, /, key: str | None = None) -> LocaleEntry | StatName:
    data = loc.get(locale)
    if data is None:
        data = loc[Locale.en_US]

    if key is None:
        return data

    return data.get(key) or loc[Locale.en_US][key]
