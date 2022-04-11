"""
Helper functions
"""
from __future__ import annotations

import asyncio
import io
import logging
import random
import re
import traceback
import typing as t
from collections import Counter, deque
from functools import partial
from string import ascii_letters

import disnake
from disnake import SelectOption
from disnake.ext import commands

from lib_types import ForbiddenChannel

SupportsSet = t.TypeVar("SupportsSet", bound=t.Hashable)
T = t.TypeVar("T")
AnyContext = commands.Context | disnake.ApplicationCommandInteraction


class _MissingSentinel:
    def __eq__(self, other: t.Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __copy__(self: T) -> T:
        return self

    def __reduce__(self) -> str:
        return "MISSING"

    def __deepcopy__(self: T, _: t.Any) -> T:
        return self


MISSING: t.Final[t.Any] = _MissingSentinel()
EMPTY_OPTION: t.Final = SelectOption(label="empty", description="Select to remove", emoji="🗑️")


async def no_op(*args: t.Any, **kwargs: t.Any) -> None:
    """Awaitable that does nothing."""
    return


def common_items(*items: t.Iterable[SupportsSet]) -> set[SupportsSet]:
    """Returns intersection of items in iterables"""
    if not items:
        return set()

    iterables = iter(items)
    result = set(next(iterables))

    for item in iterables:
        result.intersection_update(item)

    return result


def search_for(
    phrase: str, iterable: t.Iterable[str], *, case_sensitive: bool = False
) -> t.Iterator[str]:
    """Helper func capable of finding a specific string(s) in iterable.
    It is considered a match if every word in phrase appears in the name
    and in the same order. For example, both `burn scop` & `half scop`
    would match name `Half Burn Scope`, but not `burn half scop`.

    Parameters
    -----------
    phrase:
        String of whitespace-separated words.
    iterable:
        t.Iterable of strings to match against.
    case_sensitive:
        Whether the search should be case sensitive."""
    parts = (phrase if case_sensitive else phrase.lower()).split()

    for name in iterable:
        words = iter((name if case_sensitive else name.lower()).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield name


def js_format(string: str, /, **kwargs: t.Any) -> str:
    """Format a JavaScript style string using given keys and values."""
    for key, value in kwargs.items():
        string = re.sub(rf"%{re.escape(key)}%", str(value), string)

    return string


def format_count(it: t.Iterable[t.Any], /) -> t.Iterator[str]:
    return (
        f'{item}{f" x{count}" * (count > 1)}'
        for item, count
        in Counter(filter(None, it)).items())


def random_str(length: int) -> str:
    """Generates a random string of given length from ascii letters"""
    return "".join(random.sample(ascii_letters, length))


def channel_lock(
    words: t.Iterable[str] | None = None,
    regex: str | re.Pattern[str] | None = None,
    admins_bypass: bool = True,
    dm_channels_pass: bool = True
) -> t.Callable[[T], T]:
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
            _words = {"bot", "spam"}

        else:
            _words = frozenset(words)

        def sea(name: str) -> bool:
            return any(s in name for s in _words)

        search = sea

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
    events: t.Iterable[str],
    check: t.Callable[..., bool] | t.Iterable[t.Callable[..., bool]],
    timeout: float | None = None,
    return_when: t.Literal["FIRST_COMPLETED", "FIRST_EXCEPTION", "ALL_COMPLETED"] = "FIRST_COMPLETED"
) -> set[tuple[t.Any, str]]:
    """Wrapper for `Client.wait_for` accepting multiple events.
    Returns the outcome of the event and its name."""
    if isinstance(check, t.Iterable):
        tasks = {
            asyncio.create_task(client.wait_for(event, check=_check), name=event)
            for event, _check
            in zip(events, check)}

    else:
        tasks = {
            asyncio.create_task(client.wait_for(event, check=check), name=event)
            for event
            in events}

    if not tasks:
        raise ValueError("No events to await")

    done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=return_when)

    if not done:
        raise asyncio.TimeoutError

    for task in pending:
        task.cancel()

    return {(await task, task.get_name()) for task in done}


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
                msg, file=record.file, allowed_mentions=disnake.AllowedMentions.none())

        asyncio.ensure_future(task).add_done_callback(self.fallback_emit(record))


class OptionPaginator:
    """Paginator of `SelectOption`s for Select menus"""

    def __init__(
        self, up: SelectOption, down: SelectOption, options: list[SelectOption] = MISSING
    ) -> None:
        self.all_options = options or []
        self.page = 0
        self.up = up
        self.down = down

    def __len__(self) -> int:
        base = len(self.all_options)

        if base <= 25:
            return 1

        elif base <= 48:
            return 2

        full, part = divmod(base - 48, 23)

        return 2 + full + bool(part)

    def get_options(self) -> list[SelectOption]:
        """Returns a list of `SelectOption`s that should appear at current page."""
        if len(self) == 1:
            return self.all_options

        if self.page == 0:
            return self.all_options[:24] + [self.down]

        if self.page == len(self) - 1:
            return [self.up] + self.all_options[self.page*23 + 1:]

        return [self.up] + self.all_options[self.page*23 + 1:self.page*23 + 24] + [self.down]

    @property
    def options(self) -> list[SelectOption]:
        """All underlying `SelectOption`s"""
        return self.all_options

    @options.setter
    def options(self, new: list[SelectOption]) -> None:
        self.page = 0
        self.all_options = new


def abbreviate_names(names: t.Iterable[str], /) -> dict[str, set[str]]:
    """Returns dict of abbrevs:
    Energy Free Armor => EFA"""
    abbrevs: dict[str, set[str]] = {}

    for name in names:
        if len(name) < 8:
            continue

        is_single_word = " " not in name

        if (IsNotPascal := not name.isupper() and name[1:].islower()) and is_single_word:
            continue

        abbrev = {"".join(a for a in name if a.isupper()).lower()}

        if not is_single_word:
            abbrev.add(name.replace(" ", "").lower())  # Fire Fly => firefly

        if not IsNotPascal and is_single_word:  # takes care of PascalCase names
            last = 0
            for i, a in enumerate(name):
                if a.isupper():
                    if string := name[last:i].lower():
                        abbrev.add(string)

                    last = i

            abbrev.add(name[last:].lower())

        for abb in abbrev:
            abbrevs.setdefault(abb, {name}).add(name)

    return abbrevs
