from pathlib import Path

CWD = Path.cwd()
LOCALE_DIR = Path("locale/")
STATIC_DIR = Path("static/")
ASSETS_TOML = STATIC_DIR / "assets.toml"
BUFFS_TOML = STATIC_DIR / "buffs.toml"
MISSING_PNG = STATIC_DIR / "missing.png"
SILHOUETTES_DIR = STATIC_DIR / "silhouettes"
CONFIG_TOML = Path("config.toml")
DEV_ENV = Path("dev.env")
PROD_ENV = Path("prod.env")
