from collections import abc
from typing import ClassVar, Final, Protocol
from typing_extensions import Self, override

import aiohttp
import anyio
import anyio.lowlevel
import attrs

__all__ = (
    "Resource",
    "FileResource",
    "HttpResource",
    "resource",
    "set_session",
)


class Resource(abc.Hashable, Protocol):
    """Abstract protocol for a readable resource.

    Resources support reading whole or chunked iteration.
    """

    @property
    def uri(self) -> str:
        """The Uniform Identifier of the Resource."""
        ...

    async def read(self) -> bytes:
        """Read and return the entire content of the resource."""
        ...

    def iter_chunked(self, chunk_size: int, /) -> abc.AsyncIterator[bytes]:
        """Iterate over chunks of the resource."""
        ...

    @classmethod
    def from_uri(cls, uri: str, /) -> Self: ...


def resource(uri: str, /) -> Resource:
    """Get appropriate resource class for a uri, dispatching by protocol."""
    if uri.startswith("http"):
        return HttpResource.from_uri(uri)

    return FileResource.from_uri(uri)


def set_session(session: aiohttp.ClientSession, /) -> None:
    """Set the HTTP session for use by HTTP resources."""
    HttpResource.session = session


@attrs.define(hash=True)
class HttpResource(Resource):
    """Web resource from the `http(s)://` protocol."""

    url: Final[str]

    session: ClassVar[aiohttp.ClientSession]

    @property
    @override
    def uri(self) -> str:
        return self.url

    @override
    async def read(self) -> bytes:
        async with self.session.get(self.url) as response:
            return await response.read()

    @override
    async def iter_chunked(self, chunk_size: int = -1, /) -> abc.AsyncIterator[bytes]:
        async with self.session.get(self.url) as response:
            if chunk_size < 0:
                iterator = response.content.iter_any()

            else:
                iterator = response.content.iter_chunked(chunk_size)

            async for chunk in iterator:
                yield chunk

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(uri)


@attrs.define(hash=True)
class FileResource(Resource):
    """Local resource from the `file://` protocol."""

    path: Final[anyio.Path]

    @property
    @override
    def uri(self) -> str:
        return self.path.as_uri()

    @override
    async def read(self) -> bytes:
        return await self.path.read_bytes()

    @override
    async def iter_chunked(self, chunk_size: int = -1, /) -> abc.AsyncIterator[bytes]:
        async with await self.path.open("rb") as file:
            while chunk := await file.read1(chunk_size):
                yield chunk

    async def get_size(self) -> int:
        return (await self.path.stat()).st_size

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(anyio.Path(uri.removeprefix("file:").rstrip("/")))
