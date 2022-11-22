"""Utility module providing functions and classes related to disnake and/or interacting with discord."""

from __future__ import annotations

import asyncio
import importlib
import io
import logging
import pkgutil
import string
import traceback
import typing as t

from disnake import File
from disnake.abc import Messageable
from disnake.ext import commands
from typing_extensions import LiteralString

if t.TYPE_CHECKING:
    from PIL.Image import Image


class DesyncError(commands.CommandError):
    """Exception raised when due to external factors command's state goes out of sync"""


def ensure_file(data: str | bytes | io.BufferedIOBase) -> io.BufferedIOBase:
    """Creates a readable file from a string, bytes or IO object."""
    if isinstance(data, str):
        file = io.BytesIO(data.encode())

    elif isinstance(data, bytes):
        file = io.BytesIO(data)

    elif isinstance(data, io.BufferedIOBase):
        file = data

    else:
        raise TypeError(f"Unsupported data type: {data!r}")

    return file


def image_to_file(image: Image, filename: str, format: str = "png") -> File:
    """Creates a `disnake.File` object from `PIL.Image.Image`."""
    filename = validify_filename(filename, "." + format)
    stream = io.BytesIO()
    image.save(stream, format=format)
    stream.seek(0)
    return File(stream, filename)


def validify_filename(filename: str, extension: str) -> str:
    """Converts spaces to underscores, and adds extension if one isn't there."""
    filename = filename.replace(" ", "_")

    if not filename.endswith(extension):
        filename += extension

    return filename


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
                record.file = ensure_file(record.exc_text)

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


class Markdown:
    """Namespace class for functions related to markdown syntax."""

    @staticmethod
    def hyperlink(text: str, url: str) -> str:
        """Return a hyperlink to a URL."""
        return f"[{text}]({url})"

    @staticmethod
    def codeblock(text: str, lang: str = "") -> str:
        """Return text formatted with a codeblock."""
        return f"```{lang}\n{text}```"

    @staticmethod
    def strip_codeblock(text: str) -> str:
        """Return text stripped from codeblock syntax."""
        text = text.removeprefix("```").removesuffix("```")
        lang, sep, stripped = text.partition("\n")

        # coffeescript seems to be the longest lang name discord accepts
        if sep and len(lang) <= len("coffeescript"):
            return stripped

        return text


def walk_modules(
    paths: t.Iterable[str],
    prefix: str = "",
    ignore: t.Iterable[str] | t.Callable[[str], bool] | None = None
) -> t.Iterator[str]:

    if isinstance(ignore, t.Iterable):
        ignore_tup = tuple(ignore)
        ignore = lambda path: path.startswith(ignore_tup)

    seen: set[str] = set()

    for _, name, ispkg in pkgutil.iter_modules(paths, prefix):
        if ignore is not None and ignore(name):
            continue

        if not ispkg:
            yield name
            continue

        module = importlib.import_module(name)

        if hasattr(module, "setup"):
            yield name
            continue

        sub_paths: list[str] = []

        for path in module.__path__ or ():
            if path not in seen:
                seen.add(path)
                sub_paths.append(path)

        if sub_paths:
            yield from walk_modules(sub_paths, name + ".", ignore)


class monospace:
    """Collection of monospace string constants."""
    unicode_lowercase: LiteralString = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
    unicode_uppercase: LiteralString = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
    unicode_letters: LiteralString = unicode_lowercase + unicode_uppercase
    digits: LiteralString = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

    table = str.maketrans(
        string.digits + string.ascii_letters, digits + unicode_letters
    )
