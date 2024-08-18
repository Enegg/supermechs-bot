import logging
import logging.config
from pathlib import Path

import rtoml

from app.typeshed import Pathish


def config_logging(path: Pathish = "config.toml", /) -> None:
    """Configure the logging module."""
    logging.config.dictConfig(rtoml.load(Path(path))["logging"])
    logging.captureWarnings(True)
