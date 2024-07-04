import typing
from pathlib import Path

import attrs
import cattrs
import rtoml

from class_utils import attrs_from_path
from shared.utils import unfold_binary_prefix

from supermechs.gamerules import DEFAULT_GAME_RULES, GameRules

if typing.TYPE_CHECKING:
    from typeshed import Pathish

__all__ = ("CONFIG", "logging_config")

_converter = cattrs.Converter()
_converter.register_structure_hook(int, lambda val, _: unfold_binary_prefix(val))


@attrs.frozen
class _Config:
    date_format: str
    """General date format for logging purposes."""
    default_pack_url: str
    """The URL of the default item pack."""
    missing_image_url: str
    max_image_size: int
    """Maximum allowed image size, in bytes."""
    chunk_size: int
    """Size of chunk for iterative download."""
    game_rules: GameRules = DEFAULT_GAME_RULES
    """Set of rules the game shall obey."""


CONFIG = attrs_from_path("config.toml", _Config, _converter)


def logging_config(path: "Pathish" = "config.toml", /) -> dict[str, typing.Any]:
    """Read the configuration for the logging module."""
    # this is not a part of the _Config object as
    # it doesn't have to live for the lifetime of the app
    return rtoml.load(Path(path))["logging"]
