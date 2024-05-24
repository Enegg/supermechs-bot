import typing
from pathlib import Path

import attrs
import rtoml

from class_utlis import attrs_from_path

from supermechs.gamerules import GameRules

if typing.TYPE_CHECKING:
    from typeshed import Pathish

__all__ = ("CONFIG",)


@attrs.frozen
class _Config:
    date_format: str
    """General date format for logging purposes."""
    default_pack_url: str
    """The URL of the default item pack."""
    missing_image_url: str
    game_rules: GameRules = attrs.field(factory=GameRules, init=False)
    """Set of rules the game shall obey."""


CONFIG = attrs_from_path("config.toml", _Config)


def logging_config(path: "Pathish" = "config.toml", /) -> dict[str, typing.Any]:
    """Read the configuration for the logging module."""
    # this is not a part of the _Config object as
    # it doesn't have to live for the lifetime of the app
    return rtoml.load(Path(path))["logging"]
