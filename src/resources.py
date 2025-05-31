from pathlib import Path
from typing import Final, Protocol, Self, final, override

import attrs
from yarl import URL

__all__ = ("AnyResource", "FileResource", "HttpResource", "Resource", "from_uri")

type AnyResource = HttpResource | FileResource


def from_uri(uri: str, /) -> AnyResource:
    if uri.startswith(("https:", "http:")):
        return HttpResource.from_uri(uri)

    if uri.startswith("file:"):
        return FileResource.from_uri(uri)

    msg = f"Unknown protocol: {uri!r}"
    raise ValueError(msg)


class Resource(Protocol):
    """Abstract protocol for a resource."""

    @property
    def uri(self) -> str:
        """The Uniform Identifier of the Resource."""
        ...

    @classmethod
    def from_uri(cls, uri: str, /) -> Self:
        """Construct a Resource from a uri."""
        ...

@final
@attrs.frozen
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
@attrs.frozen
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
        return cls(Path.from_uri(uri))
