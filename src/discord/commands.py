import logging
from functools import wraps
from typing import Concatenate, Final, NamedTuple

import anyio

import disnake
from discord.typeshed import ClientT, CoroFunc, P
from disnake.ext import commands

_LOG = logging.getLogger(__name__)


class CancelToken(NamedTuple):
    user_id: int
    command_id: int


_COMMAND_CANCEL_SCOPES: Final[dict[CancelToken, anyio.CancelScope]] = {}


def get_cancel_token(inter: disnake.CommandInteraction[ClientT], /) -> CancelToken:
    return CancelToken(user_id=inter.author.id, command_id=inter.data.id)


def cancel_command_for(token: CancelToken, /) -> None:
    scope = _COMMAND_CANCEL_SCOPES.get(token)
    _LOG.info("Cancelling: token=%s, exists=%s", token, scope is not None)

    if scope is not None:
        scope.cancel()


def register_cancellable(
    func: CoroFunc[Concatenate[disnake.CommandInteraction[ClientT], P], object],
) -> CoroFunc[Concatenate[disnake.CommandInteraction[ClientT], P], object]:
    """Set max concurrency to 1 per user and allow for external cancellation."""

    @commands.max_concurrency(1, commands.BucketType.user)
    @wraps(func)
    async def command_callback(
        inter: disnake.CommandInteraction[ClientT], *args: P.args, **kwargs: P.kwargs
    ) -> object:
        token = get_cancel_token(inter)

        with anyio.CancelScope() as _COMMAND_CANCEL_SCOPES[token]:
            try:
                await func(inter, *args, **kwargs)

            finally:
                del _COMMAND_CANCEL_SCOPES[token]

    return command_callback
