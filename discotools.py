"""
Functions & classes to work alongside disnake
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import traceback
from collections import deque
from functools import partial
from typing import Any, Callable, Iterable, Literal, TypeVar

import disnake
from disnake.ext import commands
from disnake.utils import MISSING

T = TypeVar("T")
AnyContext = commands.Context | disnake.ApplicationCommandInteraction


def channel_lock(
    words: Iterable[str] | None = None,
    regex: str | re.Pattern[str] | None = None,
    admins_bypass: bool = True,
    dm_channels_pass: bool = True
) -> Callable[[T], T]:
    """Locks command from use in channels that are not "spam" or "bot" channels.
    It's an error to specify both words and regex.

    Parameters:
    ------------
    words:
        Iterable of words a channel name should have one of to be considered "spam" channel.
        Defaults to ["bot", "spam"]
    regex:
        A regex to match channel name with.
    admins_bypass:
        Whether to passthrough members with administrator privilege.
    dm_channels_pass:
        Whether to allow the command in DM channels.
    """
    if regex is not None:
        if words is not None:
            raise TypeError("Using both words and regex is not allowed")

        search = partial(re.search, pattern=re.compile(regex))

    else:
        if words is None:
            _words = frozenset(("bot", "spam"))

        else:
            _words = frozenset(words)

        search = lambda name: any(s in name for s in _words)

    def channel_check(inter: AnyContext) -> bool:
        channel = inter.channel

        if isinstance(channel, disnake.DMChannel):
            if not dm_channels_pass:
                raise commands.NoPrivateMessage()

            return True

        assert isinstance(inter.author, disnake.Member)

        if admins_bypass and inter.author.guild_permissions.administrator:
            return True

        if search(channel.name.lower()):
            return True

        raise ForbiddenChannel()

    return commands.check(channel_check)


async def scheduler(
    client: disnake.Client,
    events: Iterable[str],
    check: Callable[..., bool] | Iterable[Callable[..., bool]],
    timeout: float | None = None,
    return_when: Literal["FIRST_COMPLETED", "FIRST_EXCEPTION", "ALL_COMPLETED"] = "FIRST_COMPLETED"
) -> set[tuple[Any, str]]:
    """Wrapper for `Client.wait_for` accepting multiple events. Returns the outcome of the event and its name."""
    if isinstance(check, Iterable):
        tasks = {asyncio.create_task(client.wait_for(event, check=_check), name=event) for event, _check in zip(events, check)}

    else:
        tasks = {asyncio.create_task(client.wait_for(event, check=check), name=event) for event in events}

    if not tasks:
        raise ValueError("No events to await")

    done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=return_when)

    if not done:
        raise asyncio.TimeoutError

    for task in pending:
        task.cancel()

    return {(await task, task.get_name()) for task in done}


def str_to_file(fp: str | bytes | io.BufferedIOBase, filename: str | None = "file.txt") -> disnake.File:
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

    def __init__(self, *args: Any, file: disnake.File | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.file = file


class ChannelHandler(logging.Handler):
    """Handler instance dispatching logging events to a discord channel."""

    def __init__(self, channel_id: int, client: disnake.Client, level: int = logging.NOTSET) -> None:
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

    def fallback_emit(self, record: FileRecord) -> Callable[[asyncio.Future[Any]], None]:
        """Ensures the log is logged even in case of failure of sending to channel."""
        def emit(future: asyncio.Future[Any]) -> None:
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
            task = self.dest.send(msg, file=record.file, allowed_mentions=disnake.AllowedMentions.none())

        asyncio.ensure_future(task).add_done_callback(self.fallback_emit(record))


class ForbiddenChannel(commands.CheckFailure):
    """Exception raised when command is used from invalid channel."""

    def __init__(self, message: str | None = None, *args: Any) -> None:
        super().__init__(message=message or "You cannot use this command here.", *args)
