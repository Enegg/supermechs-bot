import logging
from functools import wraps
from typing import Concatenate, NamedTuple

import anyio

import disnake
from discord.typeshed import CoroFunc, P, T
from disnake.ext import commands

_LOG = logging.getLogger(__name__)


class CancelKey(NamedTuple):
    user_id: int
    command_id: int


command_cancel_scopes: dict[CancelKey, anyio.CancelScope] = {}


def get_key(inter: disnake.CommandInteraction, /) -> CancelKey:
    return CancelKey(user_id=inter.author.id, command_id=inter.data.id)


def cancel_for(key: CancelKey, /) -> None:
    scope = command_cancel_scopes.get(key)
    _LOG.info("Cancelling: key=%s, exists=%s", key, scope is not None)

    if scope is not None:
        scope.cancel()


def register_cancellable(
    func: CoroFunc[Concatenate[disnake.CommandInteraction, P], T],
) -> CoroFunc[Concatenate[disnake.CommandInteraction, P], T]:
    """Set max concurrency to 1 per user and allow for external cancellation."""

    @wraps(func)
    async def wrapper(inter: disnake.CommandInteraction, *args: P.args, **kwargs: P.kwargs) -> T:
        key = get_key(inter)

        with anyio.CancelScope() as cs:
            command_cancel_scopes[key] = cs
            try:
                return await func(inter, *args, **kwargs)

            finally:
                del command_cancel_scopes[key]

    return commands.max_concurrency(1, commands.BucketType.user)(wrapper)
