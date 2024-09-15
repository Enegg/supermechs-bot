import datetime
import logging
import logging.config
from pathlib import Path
from typing_extensions import override

import orjson
import rtoml

from app.typeshed import Pathish


# https://www.youtube.com/watch?v=9L77QExPmI0
class JsonFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.fmt_keys = fmt_keys or {}

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

        return orjson.dumps(message_dict, default=str).decode()


def config_logging(path: Pathish, /) -> None:
    """Configure the logging module."""
    logging.config.dictConfig(rtoml.load(Path(path))["logging"])
    logging.captureWarnings(True)
