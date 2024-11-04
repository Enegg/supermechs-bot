from collections import abc
from functools import partial, wraps
from typing import Any, Concatenate, ParamSpec, Self, TypeAlias
from typing_extensions import TypeVar

import anyio
import anyio.lowlevel
import attrs

__all__ = ("AsyncDeferBlock", "DeferBlock")

T = TypeVar("T", infer_variance=True)
RetT = TypeVar("RetT", infer_variance=True)
P = ParamSpec("P")

AsyncFunc: TypeAlias = abc.Callable[P, abc.Awaitable[T]]
CoroFunc: TypeAlias = abc.Callable[P, abc.Coroutine[Any, Any, T]]

# NOTE:
# If an exception happens both in the body of the context manager as well as in at least one deferred
# call, the body exception will be set as the cause of the deferred exceptions and will be overrode
# by them. Consequently, something like a CancelledError from within the block won't be propagated.


@attrs.define
class DeferBlock:
    """Context manager replicating Golang's `defer` statement.

    ### Usage:
    ```
    with DeferBlock() as defer:
        file = open(...)
        defer(file.close)
        raise RuntimeError("rest assured, we hold no files hostage")
    ```
    """

    deferred: list[abc.Callable[[], object]] = attrs.field(factory=list, init=False)

    def __call__(self, f: abc.Callable[P, object], /, *args: P.args, **kwargs: P.kwargs) -> None:
        if not (args or kwargs):
            self.deferred.append(f)
        self.deferred.append(partial(f, *args, **kwargs))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _: object, exc: BaseException | None, __: object) -> None:
        unwind_excs: list[Exception] = []

        while self.deferred:
            func = self.deferred.pop()

            try:
                func()

            except Exception as unwind_exc:
                unwind_excs.append(unwind_exc)

        if unwind_excs:
            msg = "Exceptions while unwinding defer block:"
            raise ExceptionGroup(msg, unwind_excs) from exc

    @classmethod
    def inject(cls, func: abc.Callable[Concatenate[Self, P], RetT], /) -> abc.Callable[P, RetT]:
        """Short-hand for wrapping entire function's body in a defer block."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> RetT:
            with cls() as defer:
                return func(defer, *args, **kwargs)

        return wrapper

    @classmethod
    def inject_method(
        cls, method: abc.Callable[Concatenate[T, Self, P], RetT], /
    ) -> abc.Callable[Concatenate[T, P], RetT]:
        """Short-hand for wrapping entire method's body in a defer block."""

        @wraps(method)
        def wrapper(self: T, /, *args: P.args, **kwargs: P.kwargs) -> RetT:
            with cls() as defer:
                return method(self, defer, *args, **kwargs)

        return wrapper


@attrs.define
class AsyncDeferBlock:
    """Async context manager replicating Golang's `defer` statement.

    ### Usage:
    ```
    async with AsyncDeferBlock() as defer:
        session = ClientSession()
        defer(session.close)
        raise RuntimeError("rest assured, we hold no sessions hostage")
    ```
    """

    deferred: list[AsyncFunc[[], object]] = attrs.field(factory=list, init=False)

    def __call__(self, f: AsyncFunc[P, object], /, *args: P.args, **kwargs: P.kwargs) -> None:
        if not (args or kwargs):
            self.deferred.append(f)
        self.deferred.append(partial(f, *args, **kwargs))

    async def __aenter__(self) -> Self:
        await anyio.lowlevel.checkpoint()
        return self

    async def __aexit__(self, _: object, exc: BaseException | None, __: object) -> None:
        unwind_excs: list[Exception] = []

        with anyio.CancelScope(shield=True):
            while self.deferred:
                func = self.deferred.pop()

                try:
                    await func()

                except Exception as unwind_exc:
                    unwind_excs.append(unwind_exc)

            if unwind_excs:
                msg = "Exceptions while unwinding defer block:"
                raise ExceptionGroup(msg, unwind_excs) from exc

    @classmethod
    def inject(cls, func: AsyncFunc[Concatenate[Self, P], RetT], /) -> CoroFunc[P, RetT]:
        """Short-hand for wrapping entire function's body in a defer block."""

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> RetT:
            async with cls() as defer:
                return await func(defer, *args, **kwargs)

        return wrapper

    @classmethod
    def inject_method(
        cls, method: AsyncFunc[Concatenate[T, Self, P], RetT], /
    ) -> CoroFunc[Concatenate[T, P], RetT]:
        """Short-hand for wrapping entire method's body in a defer block."""

        @wraps(method)
        async def wrapper(self: T, /, *args: P.args, **kwargs: P.kwargs) -> RetT:
            async with cls() as defer:
                return await method(self, defer, *args, **kwargs)

        return wrapper
