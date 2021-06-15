"""Functions & classes to work alongside discord.py"""
from __future__ import annotations


import asyncio
from typing import *  # type: ignore


import discord
from discord.ext import commands


VT = TypeVar("VT")
Predicate = Callable[..., bool]

# decorators
def perms(lvl: int):
    """Defines required user's lvl to access a command, following:
    1 - manage messages, 2 - manage guild, 3 - admin, 4 - guild owner, 5 - bot author"""
    async def extended_check(ctx: commands.Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        if ctx.guild is None:
            return False

        if lvl <= 4 and ctx.guild.owner_id == ctx.author.id:
            return True

        perm_keys = ('manage_messages', 'manage_guild', 'administrator')

        if lvl <= len(perm_keys):
            key = perm_keys[lvl - 1]
            return getattr(ctx.author.permissions_in(ctx.channel), key, False)  # type: ignore

        return False

    return commands.check(extended_check)


def spam_command(rate: int=None, per: float=None, bucket: commands.BucketType=commands.BucketType.default, ignore_for_admins: bool=True):
    """Ratelimits the command in channels that are not "spam" or "bot" channels.
    If rate argument is not passed, the command is disabled for those channels entirely."""
    if rate is per is None:
        cd = False

    elif rate is None or per is None:
        raise ValueError('Specified one of two cooldown arguments; both are required')

    else:
        cd = True


    def check(ctx: commands.Context) -> bool:
        channel = ctx.channel

        if isinstance(channel, discord.DMChannel):
            ctx.command.reset_cooldown(ctx)
            return True

        if ignore_for_admins and getattr(channel.permissions_for(ctx.author), 'administrator', False): # type: ignore
            ctx.command.reset_cooldown(ctx)
            return True

        name: str = channel.name.lower()

        if any(s in name for s in {'spam', 'bot'}):
            ctx.command.reset_cooldown(ctx)
            return True

        return cd


    C = TypeVar('C', bound=commands.Command[Any])

    def wrapper(command: C) -> C:
        if cd:
            command = commands.cooldown(rate, per, bucket)(command)
            command.cooldown_after_parsing = True

        return commands.check(check)(command)

    return wrapper


# embed customization
class EmbedUI(discord.Embed):
    """Preset for an embed creating a choice menu

    By default, it holds these emojis:
    0️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣🔟
    """

    NUMBERS = ('0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟')

    def __init__(self, emojis: list[str] | None=None, msg: discord.Message | commands.Context | None=None, **kwargs: Any):
        if desc := kwargs.get('desc'):
            kwargs.setdefault('description', desc)

        super().__init__(**kwargs)
        self._emojis = emojis or list(self.NUMBERS)
        self._count = len(self.emojis)

        if isinstance(msg, commands.Context):
            self._msg = msg.message

        elif msg is None or isinstance(msg, discord.Message):
            self._msg = msg

        else:
            raise TypeError('msg argument must be Message, Context or None')


    def set_default(self, ctx: commands.Context):
        """Sets embed author"""
        self.set_author(name=f'Requested by {ctx.author.display_name}', icon_url=str(ctx.author.avatar_url))
        return self


    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value: int):
        if value > len(self.emojis):
            raise ValueError('Value greater than emoji count')

        self._count = value


    @property
    def emojis(self):
        return self._emojis

    @emojis.setter
    def emojis(self, items: list[str]):
        self._emojis = items
        self.count = len(items)


    @property
    def msg(self):
        if self._msg is None:
            raise AttributeError('Message not passed to embed')

        return self._msg

    @msg.setter
    def msg(self, value: discord.Message | commands.Context):
        if not isinstance(value, (discord.Message, commands.Context)):
            raise TypeError(f'Expected Context or Message object, got {type(value)}')

        if isinstance(value, commands.Context):
            value = value.message

        self._msg = value


    async def add_options(self, add_cancel: bool=False):
        """Reacts to a message with emojis as options, returns a list of emojis"""
        reactions = self.emojis[:self.count]

        if add_cancel:
            reactions.append('❌')

        for x in reactions:
            await self.msg.add_reaction(x)

        return reactions


    async def edit(self, add_return: bool=False):
        """Edits the message"""
        await self.msg.edit(embed=self)

        if add_return:
            await self.msg.add_reaction('↩️')

        return self



def make_choice_embed(ctx: commands.Context, items: Sequence[VT], *, name_getter: Callable[[VT], str]=str, **kwargs: Any) -> discord.Embed:
    """Given 1 < len(items) <= threshold, enumerates items and puts them in embed's body.
    Embed can be customized from kwargs, those are passed to embed constructor.
    'title' has {number} argument passed for formatting.
    'description_list' has {number}, {padding} & {item} passed for formatting.

    Defaults:

    title='Found {n} items!'

    desc=description='Type a number to get the item\\n'

    desc_item='**{n:{p}}**. **{i}**'
    """
    number = len(items)

    if number < 2:
        raise ValueError('Iterable contains fewer than 2 items')

    padding = len(str(number)) + 1
    kwargs['title']  = kwargs.get('title', 'Found {n} items!').format(number=number, n=number)
    desc = kwargs.get('description', kwargs.get('desc', 'Type a number to get the item\n'))
    fill = kwargs.get('desc_item', '**{n:{p}}**. **{i}**')
    desc += '\n'.join(fill.format(number=n, item=i, padding=padding, n=n, i=i, p=padding) for n, i in enumerate(map(name_getter, items), 1))
    kwargs['description'] = desc
    kwargs['color']  = kwargs.get('color', kwargs.get('colour', ctx.author.color.value))
    kwargs['author'] = kwargs.get('author', {'name': f'Requested by {ctx.author.display_name}', 'icon_url': str(ctx.author.avatar_url)})

    try:
        embed = discord.Embed.from_dict(kwargs)  # type: ignore

    except TypeError as e:
        print(e)
        raise

    if len(embed) > 6000:
        raise ValueError('Embed body exceeded 6000 character limit')

    return embed


async def user_choice(ctx: commands.Context, items: Sequence[VT], msg_args: dict[str, Any],
        predicate: Callable[[discord.Message], bool]=None, timeout: float=None) -> tuple[discord.Message, Optional[VT]]:
    """Creates a message from msg_args and sends it to passed Context's channel.
    Awaits a message from Context's author that meets the predicate (default implementation checks author, channel and content.isdigit())
    and returns a tuple of message sent and an item that matched the input or None if the input was invalid."""

    bot_msg = await ctx.send(**msg_args)

    if predicate is None:
        def check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        predicate = check

    try:
        reply = await ctx.bot.wait_for('message', check=predicate, timeout=timeout)

    except asyncio.TimeoutError:
        await bot_msg.add_reaction('⏰')
        return bot_msg, None

    else:
        choice = int(reply.content) - 1

        if 0 <= choice < len(items):
            item = items[choice]
            await reply.delete()

        else:
            await reply.add_reaction('❌')
            return bot_msg, None

    return bot_msg, item


async def scheduler(ctx: commands.Context, events: Iterable[str], check: Predicate | Iterable[Predicate], timeout: float = None,
                    return_when: Literal['FIRST_COMPLETED', 'FIRST_EXCEPTION', 'ALL_COMPLETED'] = 'FIRST_COMPLETED') -> set[tuple[Any, str]]:
    """Wrapper for asyncio.wait designed for discord events. Returns the outcome of the event and its name."""
    if not events:
        raise ValueError('No events to await')

    if isinstance(check, Iterable):
        tasks = {asyncio.create_task(ctx.bot.wait_for(event, check=_check), name=event) for event, _check in zip(events, check)}

    else:
        tasks = {asyncio.create_task(ctx.bot.wait_for(event, check=check), name=event) for event in events}

    done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=return_when)

    if not done:
        raise asyncio.TimeoutError

    for task in pending:
        task.cancel()

    return {(await task, task.get_name()) for task in done}



class Flag(commands.Converter):
    """Converter for CLI style flags

    Usage: command_name(ctx, arg: Flag['-foo', '-bar'])

    Returns flags found in command arguments
    """
    flags: tuple[str, ...]

    def __new__(cls, *, flags: tuple[str, ...]=None):
        self = super(Flag, cls).__new__(cls)
        self.flags = flags
        return self


    def __class_getitem__(cls, flags: str | tuple[str, ...]):
        if isinstance(flags, str):
            flags = (flags,)

        elif not isinstance(flags, tuple) or any(not isinstance(i, str) for i in flags):
            raise TypeError(f'{type(cls).__name__}[...] only accepts literal strings')

        return cls(flags=flags)


    def __contains__(self, key: str) -> bool:
        return bool(self.flags) and key in self.flags


    def __repr__(self):
        return f"{type(self).__name__}{'[' + ', '.join(self.flags) + ']' if self.flags else ''}"


    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if self.flags is None:
            raise AttributeError('Converter used without specifying flags')

        arg = arg.lower()

        for flag in self.flags:
            if flag.startswith(arg):
                return flag

        else:
            raise commands.BadArgument



def async_from_sync(loop: asyncio.AbstractEventLoop, coro: Awaitable[Any], callback: Callable[[asyncio.Task], Any]=None):
    task = loop.create_task(coro)

    if callback:
        task.add_done_callback(callback)
