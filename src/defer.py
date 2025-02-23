from collections import abc
from contextlib import nullcontext
from functools import partial
from typing import Generic, ParamSpec, final
from typing_extensions import TypeVar

import anyio
import anyio.lowlevel
import attrs

__all__ = ("Defer",)

T = TypeVar("T", infer_variance=True)
RetT = TypeVar("RetT", object, abc.Awaitable[object], infer_variance=True)
P = ParamSpec("P")

# NOTE:
# If an exception happens both in the body of the context manager as well as in at least one deferred
# call, the body exception will be set as the cause of the deferred exceptions and will be overrode
# by them. Consequently, something like a CancelledError from within the block won't be propagated.


@final  # typing and injections would surely break
@attrs.define
class Defer(Generic[RetT]):
    """Context manager replicating Golang's `defer` statement.

    ### Usage:
    ```
    with Defer() as defer:
        file = open(...)
        defer(file.close)
        raise RuntimeError("rest assured, we hold no files hostage")
    ```

    Parameters
    ----------
    shield: bool, optional
        When used in an `async with` block, this parameter controls whether the deferred calls
        should be shielded from cancellation.
    """

    shield: bool = attrs.field(default=False, kw_only=True)
    deferred: list[abc.Callable[[], RetT]] = attrs.field(factory=list, init=False)

    def __call__(self, f: abc.Callable[P, RetT], /, *args: P.args, **kwargs: P.kwargs) -> None:
        self.deferred.append(partial(f, *args, **kwargs) if args or kwargs else f)

    def __enter__(self: "Defer[object]") -> "Defer[object]":
        return self

    def __exit__(self: "Defer[object]", *_: object) -> None:
        unwind_excs: list[Exception] = []

        while self.deferred:
            func = self.deferred.pop()

            try:
                func()

            except Exception as unwind_exc:
                unwind_excs.append(unwind_exc)

        if unwind_excs:
            msg = "Exceptions while unwinding defer block:"
            raise ExceptionGroup(msg, unwind_excs)

    async def __aenter__(self: "Defer[abc.Awaitable[object]]") -> "Defer[abc.Awaitable[object]]":
        await anyio.lowlevel.checkpoint_if_cancelled()
        return self

    async def __aexit__(self: "Defer[abc.Awaitable[object]]", *_: object) -> None:
        unwind_excs: list[Exception] = []

        with anyio.CancelScope(shield=True) if self.shield else nullcontext():
            while self.deferred:
                func = self.deferred.pop()

                try:
                    await func()

                except Exception as unwind_exc:
                    unwind_excs.append(unwind_exc)

            if unwind_excs:
                msg = "Exceptions while unwinding defer block:"
                raise ExceptionGroup(msg, unwind_excs)
