"""A utility module providing functions and classes related to disnake and/or interacting with discord."""

from __future__ import annotations

import asyncio
import io
import logging
import traceback
import typing as t

from disnake import File
from disnake.abc import Messageable
from disnake.ext import commands

if t.TYPE_CHECKING:
    from PIL.Image import Image


class DesyncError(commands.CommandError):
    """Exception raised when due to external factors command's state goes out of sync"""

    pass


def str_to_file(
    fp: str | bytes | io.TextIOBase | io.BufferedIOBase, filename: str | None = "file.txt"
) -> File:
    """Creates a disnake.File from a string, bytes or IO object."""
    match fp:
        case str():
            file = io.StringIO(fp)

        case bytes():
            file = io.BytesIO(fp)

        case _:
            file = fp

    return File(file, filename)  # pyright: ignore[reportGeneralTypeIssues]


def image_to_file(image: Image, filename: str | None = None, format: str = "png") -> File:
    """Creates a `disnake.File` object from `PIL.Image.Image`."""
    # not using with as the stream is closed by the File object
    if filename is not None:
        filename = filename.replace(" ", "_")

        ext = "." + format

        if not filename.endswith(ext):
            filename += ext

    stream = io.BytesIO()
    image.save(stream, format=format)
    stream.seek(0)
    return File(stream, filename)


class FileRecord(logging.LogRecord):
    """LogRecord with extra file attribute"""

    def __init__(self, *args: t.Any, file: File | None = None, **kwargs: t.Any) -> None:
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
                record.file = str_to_file(record.exc_text, "traceback.py")

            else:
                if not msg.endswith("\n"):
                    msg += "\n"

                msg += "```py\n"
                msg += record.exc_text
                msg += "```"

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
            coro = self.destination.send(msg, file=record.file)

        asyncio.create_task(coro).add_done_callback(self.fallback_emit(record))


class ReprMixin:
    """Class for programmatic __repr__ creation."""

    __repr_attributes__: t.Iterable[str]
    __slots__ = ()

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs} at 0x{id(self):016X}>"


def add_plural_s(text: str, value: int, plural: str = "s") -> str:
    if value != 1:
        return text + plural

    return text


def hyperlink(text: str, url: str) -> str:
    """Return a hyperlink to a URL."""
    return f"[{text}]({url})"
