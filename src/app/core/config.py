import attrs
import cattrs

from app import paths
from app.class_utils import attrs_from_path
from app.utils import unfold_binary_prefix

from supermechs.gamerules import DEFAULT_GAME_RULES, GameRules

__all__ = ("CONFIG",)

_converter = cattrs.Converter()
_converter.register_structure_hook(int, lambda val, _: unfold_binary_prefix(val))


@attrs.frozen
class Config:
    date_format: str
    """General date format for logging purposes."""
    default_pack_url: str
    """The URL of the default item pack."""
    missing_image_url: str
    """Placeholder image url."""
    max_image_size: int
    """Maximum allowed image size, in bytes."""
    chunk_size: int = 1024**2
    """Size of chunk for iterative download."""
    game_rules: GameRules = DEFAULT_GAME_RULES
    """Set of rules the game shall obey."""
    # no need to store logging config here for the app's lifetime


CONFIG = attrs_from_path(Config, paths.CONFIG, _converter)
