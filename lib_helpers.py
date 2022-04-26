from __future__ import annotations

import asyncio
import io
import logging
import traceback
import typing as t
from collections import deque

import disnake
from disnake.ext import commands

from utils import MISSING

if t.TYPE_CHECKING:
    from bot import SMBot


class MessageInteraction(disnake.MessageInteraction):
    bot: SMBot


class ApplicationCommandInteraction(disnake.ApplicationCommandInteraction):
    bot: SMBot


class ForbiddenChannel(commands.CheckFailure):
    """Exception raised when command is used from invalid channel."""

    def __init__(self, message: str | None = None, *args: t.Any) -> None:
        super().__init__(message=message or "You cannot use this command here.", *args)


def str_to_file(
    fp: str | bytes | io.BufferedIOBase, filename: str | None = "file.txt"
) -> disnake.File:
    """Creates a disnake.File from a string, bytes or IO object."""
    match fp:
        case str():
            file = io.BytesIO(fp.encode())

        case bytes():
            file = io.BytesIO(fp)

        case _:
            file = fp

    return disnake.File(file, filename)


class FileRecord(logging.LogRecord):
    """LogRecord with extra file attribute"""

    def __init__(self, *args: t.Any, file: disnake.File | None = None, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.file = file


class ChannelHandler(logging.Handler):
    """Handler instance dispatching logging events to a discord channel."""

    def __init__(
        self, channel_id: int, client: disnake.Client, level: int = logging.NOTSET
    ) -> None:
        super().__init__(level)
        self.dest: disnake.abc.Messageable = MISSING
        self.queue: deque[FileRecord] = deque()

        def setter(future: asyncio.Future[None]) -> None:
            channel = client.get_channel(channel_id)

            if not isinstance(channel, disnake.abc.Messageable):
                raise TypeError("Channel is not Messengable")

            self.dest = channel

            while self.queue:
                self.emit(self.queue.popleft())

        asyncio.ensure_future(client.wait_until_ready()).add_done_callback(setter)

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

    def fallback_emit(self, record: FileRecord) -> t.Callable[[asyncio.Future[t.Any]], None]:
        """Ensures the log is logged even in case of failure of sending to channel."""

        def emit(future: asyncio.Future[t.Any]) -> None:
            if future.exception():
                print(super().format(record))

            return

        return emit

    def emit(self, record: FileRecord) -> None:
        if self.dest is MISSING:
            self.queue.append(record)
            return

        msg = self.format(record)

        if record.file is None:
            task = self.dest.send(msg, allowed_mentions=disnake.AllowedMentions.none())

        else:
            task = self.dest.send(
                msg, file=record.file, allowed_mentions=disnake.AllowedMentions.none()
            )

        asyncio.ensure_future(task).add_done_callback(self.fallback_emit(record))
