import typing
import typing_extensions as typing_
from collections import abc

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


class Resource(abc.Hashable, typing.Protocol):
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
    def from_uri(cls, uri: str, /) -> typing_.Self: ...


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
    url: typing.Final[str]

    session: typing.ClassVar[aiohttp.ClientSession]

    @property
    @typing_.override
    def uri(self) -> str:
        return self.url

    @typing_.override
    async def read(self) -> bytes:
        async with self.session.get(self.url) as response:
            return await response.read()

    @typing_.override
    async def iter_chunked(self, chunk_size: int, /) -> abc.AsyncIterator[bytes]:
        async with self.session.get(self.url) as response:
            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk

    @classmethod
    @typing_.override
    def from_uri(cls, uri: str, /) -> typing_.Self:
        return cls(uri)


@attrs.define(hash=True)
class FileResource(Resource):
    """Local resource from the `file://` protocol."""
    path: typing.Final[anyio.Path]

    @property
    @typing_.override
    def uri(self) -> str:
        return self.path.as_uri()

    @typing_.override
    async def read(self) -> bytes:
        return await self.path.read_bytes()

    @typing_.override
    async def iter_chunked(self, chunk_size: int, /) -> abc.AsyncIterator[bytes]:
        async with await self.path.open("rb") as file:
            yield await file.read1(chunk_size)

    async def get_size(self) -> int:
        return (await self.path.stat()).st_size

    @classmethod
    @typing_.override
    def from_uri(cls, uri: str, /) -> typing_.Self:
        return cls(anyio.Path(uri.removeprefix("file:").rstrip("/")))
