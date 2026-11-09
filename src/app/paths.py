from pathlib import Path

CWD = Path.cwd()
LOCALE_DIR = Path("locale/")
LOCALE_FILE_EXT = ".toml"
STATIC_DIR = Path("static/")
ASSETS_TOML = STATIC_DIR / "assets.toml"
EMOJIS_TOML = STATIC_DIR / ".emojis.toml"
MISSING_PNG = STATIC_DIR / "missing.png"
ICONS_PNG_DIR = STATIC_DIR / "icons/png/"
ICONS_SVG_DIR = STATIC_DIR / "icons/svg/"
LOGS_DIR = Path("logs/")
DEV_ENV = Path("dev.env")
PROD_ENV = Path("prod.env")
PLUGINS_PACKAGE = "extensions"
