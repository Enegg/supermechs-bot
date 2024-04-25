import typing
import typing_extensions as typing_
from collections import abc
from pathlib import Path

import attrs
import rtoml

from supermechs.gamerules import GameRules

__all__ = ("CONFIG",)


@attrs.frozen
class _Config:
    logging: dict[str, typing.Any]
    """Configuration for the logging module."""
    date_format: str
    """General date format for logging purposes."""

    embed_tips: abc.Sequence[str]
    """Sequence of embed footers randomly displayed to users."""
    default_pack_url: str
    """The URL of the default item pack."""
    missing_image_url: str
    game_rules: GameRules = attrs.field(factory=GameRules, init=False)
    """Set of rules the game shall obey."""

    @classmethod
    def from_path(cls, path: Path, /) -> typing_.Self:
        _config = rtoml.load(path)
        return cls(
            _config["logging"],
            _config["bot"]["DATE_FORMAT"],
            _config["SM"]["EMBED_TIPS"],
            _config["SM"]["DEFAULT_PACK_URL"],
            _config["SM"]["MISSING_IMAGE_URL"],
        )


CONFIG = _Config.from_path(Path("config.toml"))
