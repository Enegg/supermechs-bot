# https://www.youtube.com/watch?v=9L77QExPmI0
# TODO (3.12): QueueHandler/QueueListener
import copy
import datetime
import io
import logging
import logging.config
from collections import abc
from pathlib import Path
from typing import override

import orjson
import rtoml

from app import paths
from app.typeshed import Pathish
from app.utils import strip_cwd

BUILTIN_KEYS = frozenset({
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
})  # fmt: skip

type FilterType = logging.Filter | abc.Callable[[logging.LogRecord], logging.LogRecord | bool]
"""Type of an object acceptable as a Filter."""


def normalize_record_path(record: logging.LogRecord) -> logging.LogRecord:
    if record.pathname == "(unknown file)":
        return record

    try:
        path = strip_cwd(record.pathname, paths.CWD)

    except ValueError:
        return record

    # TODO (3.13): copy.replace?
    record = copy.copy(record)
    record.pathname = path
    return record


def get_path_normalizer() -> FilterType:
    return normalize_record_path


def patch_file_handler() -> None:
    _base_open = logging.FileHandler._open

    def _open(self: logging.FileHandler) -> io.TextIOWrapper:
        Path(self.baseFilename).parent.mkdir(exist_ok=True, parents=True)
        return _base_open(self)

    logging.FileHandler._open = _open


class JsonFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys: abc.Mapping[str, str] = {},
    ) -> None:
        super().__init__()
        self.fmt_keys = fmt_keys

    @override
    def format(self, record: logging.LogRecord) -> str:
        base_fields = {
            "message": record.getMessage(),
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.UTC
            ).isoformat(),
        }
        if record.exc_info is not None:
            base_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            base_fields["stack_info"] = self.formatStack(record.stack_info)

        message_dict = {
            key: msg_val
            if (msg_val := base_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message_dict.update(base_fields)

        for key, value in record.__dict__.items():
            if key not in BUILTIN_KEYS:
                message_dict[key] = value  # noqa: PERF403

        return orjson.dumps(message_dict, default=str).decode()


def config_logging(path: Pathish, /) -> None:
    """Configure the logging module."""
    config = rtoml.load(Path(path))["logging"]
    patch_file_handler()
    logging.config.dictConfig(config)
    logging.captureWarnings(True)
