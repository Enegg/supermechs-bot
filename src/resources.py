from collections import abc
from typing import ClassVar, Final, Protocol, final
from typing_extensions import Self, override

import anyio
import attrs

__all__ = ("FileResource", "HttpResource", "Resource")


class Resource(abc.Hashable, Protocol):
    """Abstract protocol for a resource."""

    _protocol_dispatch: ClassVar[dict[str, type[Self]]] = {}

    @property
    def uri(self) -> str:
        """The Uniform Identifier of the Resource."""
        ...

    @classmethod
    def from_uri(cls, uri: str, /) -> Self:
        """Construct a Resource from a uri."""
        protocol, _, rest = uri.partition("://")

        if not rest:
            msg = "uri has no protocol"
            raise ValueError(msg)

        subcls = cls._protocol_dispatch.get(protocol)

        if subcls is None:
            msg = f"Unknown protocol: {protocol}"
            raise NotImplementedError(msg)

        return subcls.from_uri(uri)

    @classmethod
    def register(cls, subcls: type[Self], *protocols: str) -> None:
        for protocol in protocols:
            cls._protocol_dispatch[protocol] = subcls


@final
@attrs.define(hash=True)
class HttpResource(Resource):
    """Web resource from the `http(s)://` protocol."""

    url: Final[str]

    @property
    @override
    def uri(self) -> str:
        return self.url

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(uri)


@final
@attrs.define(hash=True)
class FileResource(Resource):
    """Local resource from the `file://` protocol."""

    path: Final[anyio.Path]

    @property
    @override
    def uri(self) -> str:
        return self.path.as_uri()

    async def read(self) -> bytes:
        return await self.path.read_bytes()

    async def get_size(self) -> int:
        return (await self.path.stat()).st_size

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(anyio.Path(uri.removeprefix("file://")))


# NOTE: do it this way as attrs clashes with __init_subclass__
Resource.register(HttpResource, "http", "https")
Resource.register(FileResource, "file")
