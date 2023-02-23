import asyncio
import io
import logging
import traceback
import typing as t

from disnake import File
from disnake.abc import Messageable

from .text_formatting import Markdown

__all__ = ("FileRecord", "ChannelHandler")


class FileRecord(logging.LogRecord):
    """LogRecord with extra file attribute."""

    def __init__(
        self, *args: t.Any, file: io.BufferedIOBase | None = None, **kwargs: t.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.file = file


class ChannelHandler(logging.Handler):
    """Handler instance dispatching logging events to a discord channel."""

    def __init__(self, channel: Messageable, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.destination = channel

    @staticmethod
    def format(record: FileRecord) -> str:
        msg = record.getMessage()

        if record.exc_info:
            if not record.exc_text:
                with io.StringIO() as sio:
                    traceback.print_exception(*record.exc_info, file=sio)
                    stack = sio.getvalue()

                record.exc_text = stack

            if len(record.exc_text) + len(msg) + 8 > 2000:
                record.file = io.BytesIO(record.exc_text.encode())

            else:
                if not msg.endswith("\n"):
                    msg += "\n"

                msg += Markdown.codeblock(record.exc_text, "py")

        return msg

    @staticmethod
    def fallback_emit(record: FileRecord) -> t.Callable[[asyncio.Future[t.Any]], None]:
        """Ensures the log is logged even in case of failure of sending to channel."""

        def emit(future: asyncio.Future[t.Any]) -> None:
            if future.exception():
                print(super().format(record))

            return

        return emit

    def emit(self, record: FileRecord) -> None:
        msg = self.format(record)

        if record.file is None:
            coro = self.destination.send(msg)

        else:
            coro = self.destination.send(msg, file=File(record.file, "traceback.py"))

        asyncio.create_task(coro).add_done_callback(self.fallback_emit(record))
