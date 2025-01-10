from collections import abc
from pathlib import Path
from typing import Final, Protocol, Self, final
from typing_extensions import override

import attrs
from yarl import URL

__all__ = ("FileResource", "HttpResource", "Resource")


class Resource(abc.Hashable, Protocol):
    """Abstract protocol for a resource."""

    _protocol_registry: Final[dict[str, type[Self]]] = {}

    @property
    def uri(self) -> str:
        """The Uniform Identifier of the Resource."""
        ...

    @override
    def __hash__(self) -> int:
        return hash(self.uri)

    @classmethod
    def from_uri(cls, uri: str, /) -> Self:
        """Construct a Resource from a uri."""
        protocol, _, rest = uri.partition("://")

        if not rest:
            msg = "uri has no protocol"
            raise ValueError(msg)

        subcls = cls._protocol_registry.get(protocol)

        if subcls is None:
            msg = f"Unknown protocol: {protocol}"
            raise NotImplementedError(msg)

        return subcls.from_uri(uri)

    @classmethod
    def _register(cls, subcls: type[Self], *protocols: str) -> None:
        for protocol in protocols:
            cls._protocol_registry[protocol] = subcls


@final
@attrs.define(hash=True, frozen=True)
class HttpResource(Resource):
    """Web resource from the `http(s)://` protocol."""

    url: Final[URL]

    @property
    @override
    def uri(self) -> str:
        return str(self.url)

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(URL(uri))


@final
@attrs.define(hash=True, frozen=True)
class FileResource(Resource):
    """Local resource from the `file://` protocol."""

    path: Final[Path]

    @property
    @override
    def uri(self) -> str:
        return self.path.as_uri()

    @classmethod
    @override
    def from_uri(cls, uri: str, /) -> Self:
        return cls(Path(uri.removeprefix("file://")))


Resource._register(HttpResource, "http", "https")  # pyright: ignore[reportPrivateUsage]
Resource._register(FileResource, "file")  # pyright: ignore[reportPrivateUsage]