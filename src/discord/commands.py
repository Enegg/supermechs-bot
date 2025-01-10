import logging
from functools import wraps
from typing import Concatenate, Final, NamedTuple

import anyio

import disnake
from discord.typeshed import ClientT, CoroFunc, P
from disnake.ext import commands

_LOG = logging.getLogger(__name__)


class CancelKey(NamedTuple):
    user_id: int
    command_id: int


_command_cancel_scopes: Final[dict[CancelKey, anyio.CancelScope]] = {}


def get_key(inter: disnake.CommandInteraction[ClientT], /) -> CancelKey:
    return CancelKey(user_id=inter.author.id, command_id=inter.data.id)


def cancel_for(key: CancelKey, /) -> None:
    scope = _command_cancel_scopes.get(key)
    _LOG.info("Cancelling: key=%s, exists=%s", key, scope is not None)

    if scope is not None:
        scope.cancel()


def register_cancellable(
    func: CoroFunc[Concatenate[disnake.CommandInteraction[ClientT], P], object],
) -> CoroFunc[Concatenate[disnake.CommandInteraction[ClientT], P], object]:
    """Set max concurrency to 1 per user and allow for external cancellation."""

    @wraps(func)
    async def wrapper(
        inter: disnake.CommandInteraction[ClientT], *args: P.args, **kwargs: P.kwargs
    ) -> object:
        key = get_key(inter)

        with anyio.CancelScope() as _command_cancel_scopes[key]:
            try:
                await func(inter, *args, **kwargs)

            finally:
                del _command_cancel_scopes[key]

    return commands.max_concurrency(1, commands.BucketType.user)(wrapper)
