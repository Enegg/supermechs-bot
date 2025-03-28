import logging
import logging.config

from app import paths
from app.core.logging import config_logging

config_logging(paths.CONFIG_TOML)

logging.getLogger("foo").info("Hi")
logging.getLogger("disnake").info("Hi")
