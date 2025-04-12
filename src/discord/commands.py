import enum
import logging
from functools import wraps
from typing import Any, Final, NamedTuple

import anyio

import disnake
from disnake.ext import commands

_LOG = logging.getLogger(__name__)


class CustomEvent(enum.StrEnum):
    cancel = "command_cancellable"

    @property
    def listener_name(self) -> str:
        return f"on_{self.value}"


# disnake lies about inheriting from Enum, and renamed _member_names_ :pain:
assert CustomEvent._member_map_.keys().isdisjoint(disnake.Event._enum_member_names_)  # pyright: ignore[reportUnknownArgumentType, reportAttributeAccessIssue]

type AnyContext = commands.Context[commands.Bot] | disnake.CommandInteraction[disnake.Client]


class CancelToken(NamedTuple):
    user_id: int
    command_id: int


_COMMAND_CANCEL_SCOPES: Final[dict[CancelToken, anyio.CancelScope]] = {}


def get_cancel_token(inter: disnake.CommandInteraction[disnake.Client], /) -> CancelToken:
    return CancelToken(user_id=inter.author.id, command_id=inter.data.id)


def cancel_command_for(token: CancelToken, /) -> None:
    scope = _COMMAND_CANCEL_SCOPES.get(token)
    _LOG.info("Cancelling: token=%s, exists=%s", token, scope is not None)

    if scope is not None:
        scope.cancel()


async def _on_concurrent_command(ctx: AnyContext, exc: commands.CommandError) -> bool:
    if (
        not isinstance(exc, commands.MaxConcurrencyReached)
        or exc.number != 1
        or exc.per is not commands.BucketType.user
    ):
        return False

    ctx.bot.dispatch(CustomEvent.cancel, ctx)
    return True


def register_cancellable[CommandT: commands.InvokableApplicationCommand](
    command: CommandT,
) -> CommandT:
    """Enable cancellation of a command.

    Cancellable commands have their concurrency set to 1 per user.
    """
    func = command._callback  # pyright: ignore[reportPrivateUsage]

    @wraps(func)
    async def command_callback(
        inter: disnake.CommandInteraction[disnake.Client], *args: Any, **kwargs: Any
    ) -> None:
        token = get_cancel_token(inter)

        with anyio.CancelScope() as _COMMAND_CANCEL_SCOPES[token]:
            try:
                await func(inter, *args, **kwargs)

            finally:
                del _COMMAND_CANCEL_SCOPES[token]

    command._callback = command_callback  # pyright: ignore[reportPrivateUsage]

    max_concurrency = commands.MaxConcurrency(1, per=commands.BucketType.user, wait=False)
    command._max_concurrency = max_concurrency  # pyright: ignore[reportPrivateUsage]
    command.error(_on_concurrent_command)
    return command
