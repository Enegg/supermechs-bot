# https://youtu.be/9L77QExPmI0
# TODO (3.12): QueueHandler/QueueListener
import datetime as dt
import logging
from collections import abc
from typing import override

import orjson


class JsonFormatter(logging.Formatter):
    LOG_RECORD_BUILTIN_KEYS = frozenset({
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
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(),
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
            if key not in __class__.LOG_RECORD_BUILTIN_KEYS:
                message_dict[key] = value  # noqa: PERF403

        return orjson.dumps(message_dict, default=str).decode()
