from pathlib import Path

__all__ = ("ASSETS", "LOCALE", "PLUGINS")

_cwd = Path.cwd()

LOCALE = _cwd / "locale/"
ASSETS = _cwd / "assets/assets.toml"
SILHOUETTE = ASSETS.parent / "silhouette.png"
PLUGINS = _cwd / "app/extensions/"
CONFIG = _cwd / "config.toml"
STATE = _cwd / ".state/"


def is_local(url: str, /) -> bool:
    return url.startswith("file://")
