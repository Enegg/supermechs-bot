"""Functions & classes to work alongside discord.py"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import traceback
from collections import deque
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, TypeVar

import disnake
from disnake.ext import commands
from disnake.utils import MISSING

if TYPE_CHECKING:
    from types import TracebackType

T = TypeVar('T')
AnyContext = commands.Context | disnake.ApplicationCommandInteraction

def channel_lock(
    words: Iterable[str]=None,
    regex: str | re.Pattern[str]=None,
    admins_bypass: bool=True,
    dm_channels_pass: bool=True
) -> Callable[[T], T]:
    """Locks command from use in channels that are not "spam" or "bot" channels.
    It's an error to specify both words and regex.

    Parameters:
    ------------
    words:
        Iterable of words a channel name should have one of to be considered "spam" channel.
        Defaults to ['bot', 'spam']
    regex:
        A regex to match channel name with.
    admins_bypass:
        Whether to passthrough members with administrator privilege.
    dm_channels_pass:
        Whether to allow the command in DM channels.
    """
    if regex is not None:
        if words is not None:
            raise TypeError('Using both words and regex is not allowed')

        search = partial(re.search, pattern=re.compile(regex))

    else:
        if words is None:
            _words = frozenset(('bot', 'spam'))

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
    timeout: float = None,
    return_when: Literal['FIRST_COMPLETED', 'FIRST_EXCEPTION', 'ALL_COMPLETED'] = 'FIRST_COMPLETED'
) -> set[tuple[Any, str]]:
    """Wrapper for `Client.wait_for` accepting multiple events. Returns the outcome of the event and its name."""
    if isinstance(check, Iterable):
        tasks = {asyncio.create_task(client.wait_for(event, check=_check), name=event) for event, _check in zip(events, check)}

    else:
        tasks = {asyncio.create_task(client.wait_for(event, check=check), name=event) for event in events}

    if not tasks:
        raise ValueError('No events to await')


    done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=return_when)

    if not done:
        raise asyncio.TimeoutError

    for task in pending:
        task.cancel()

    return {(await task, task.get_name()) for task in done}


class DiscordFormatter(logging.Formatter):
    @staticmethod
    def formatException(exc_info: tuple[type[BaseException] | None, BaseException | None, TracebackType | None]) -> str:
        """Format and return the specified exception information as discord markdown code block."""
        with io.StringIO() as sio:
            sio.write('```py\n')
            traceback.print_exception(*exc_info, file=sio)
            sio.write('```')
            return sio.getvalue()


class ChannelHandler(logging.Handler):
    """Handler instance dispatching logging events to a discord channel."""
    def __init__(self, channel_id: int, client: disnake.Client, level: int=logging.NOTSET) -> None:
        super().__init__(level)
        self.client = client
        self.dest: disnake.abc.Messageable = MISSING
        self.queue: deque[logging.LogRecord] = deque()
        self.formatter = DiscordFormatter()


        def setter(future: asyncio.Future[None]) -> None:
            channel = client.get_channel(channel_id)

            if not isinstance(channel, disnake.abc.Messageable):
                raise TypeError('Channel is not Messengable')

            self.dest = channel

            while self.queue:
                self.emit(self.queue.popleft())

        client.loop.create_task(client.wait_until_ready()).add_done_callback(setter)


    def emit(self, record: logging.LogRecord) -> None:
        if self.dest is MISSING:
            self.queue.append(record)
            return

        msg = self.format(record)
        self.client.loop.create_task(self.dest.send(msg, allowed_mentions=disnake.AllowedMentions.none()))


class ForbiddenChannel(commands.CheckFailure):
    """Exception raised when command is used from invalid channel."""

    def __init__(self, message: str = None, *args: Any) -> None:
        super().__init__(message=message or 'You cannot use this command here.', *args)
