from __future__ import annotations

import contextlib
import io
import os
import pathlib
import typing as t

import aiohttp
import attrs
import orjson
import yarl
from typing_extensions import Self, override

from shared import SESSION_CTX

if t.TYPE_CHECKING:
    from PIL.Image import Image

Pathish = os.PathLike[str] | str
"""A literal file or path."""

Urlish = yarl.URL | str
"""A literal URL."""


def ensure_path(pathish: Pathish) -> pathlib.Path:
    """Convert a path-like object to a `pathlib.Path` instance."""
    return pathlib.Path(pathish)


def ensure_url(urlish: Urlish) -> yarl.URL:
    """Convert a url-like object to a `yarl.URL` instance."""
    return yarl.URL(urlish)


def ensure_valid_path(pathish: Pathish) -> pathlib.Path:
    """Convert a path-like object to a `pathlib.Path` instance which points to a valid file."""
    path = ensure_path(pathish)

    if not path.is_file():
        raise ValueError("Path does not exist")

    return path


def ensure_valid_url(urlish: Urlish) -> yarl.URL:
    """Convert a url-like object to a `yarl.URL` instance which is a valid url."""
    url = ensure_url(urlish)

    if not url.scheme.startswith("http"):
        raise ValueError("URL is not valid")

    return url


def webresource_size(response: aiohttp.ClientResponse) -> int | None:
    """Get the content length of a web resource, if possible."""
    length = response.content_length

    if length is None:
        if (range_ := response.headers.get(aiohttp.hdrs.CONTENT_RANGE)) is not None:
            length = int(range_[range_.rfind("/") :])

    return length


class Resource:
    """Base for any uploadable or downloadable representation of information."""

    __slots__ = ()

    @property
    def url(self) -> yarl.URL:
        """URL of the resource."""
        raise NotImplementedError

    @property
    def filename(self) -> str:
        """Filename of the resource."""
        raise NotImplementedError

    @property
    def extension(self) -> str | None:
        """File extension, if there is one."""
        _, ext = os.path.splitext(self.filename)
        return ext or None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(url={self.url!r}, filename={self.filename!r})"

    async def get_size(self) -> int | None:
        """Get the size of the resource, in bytes, if possible."""
        return None

    async def read(self) -> bytes:
        """Read the data of the resource, all at once."""
        raise NotImplementedError

    async def open(self) -> io.BufferedIOBase:
        """Get a (possibly arbitrary) file pointer for the resource. Remember to close the file afterwards."""
        raise NotImplementedError

    def stream(self) -> contextlib.AbstractAsyncContextManager[t.Any]:
        """Stream context manager for the resource."""
        raise NotImplementedError

    async def json(self) -> t.Any:
        """Get the contents of the resource loaded as json."""
        raise NotImplementedError


@attrs.define
class URL(Resource):
    """A URL that represents a web resource."""

    url: yarl.URL = attrs.field(converter=ensure_valid_url)
    """URL of the resource."""

    if t.TYPE_CHECKING:
        def __init__(self, url: Urlish, /) -> None:
            ...

    @property
    @override
    def filename(self) -> str:
        return os.path.basename(self.url.path)

    @override
    async def get_size(self) -> int | None:
        async with SESSION_CTX.get().head(self.url) as response:
            return webresource_size(response)

    @override
    async def read(self) -> bytes:
        async with self.stream() as stream:
            return await stream.read()

    @override
    async def open(self) -> io.BytesIO:
        return io.BytesIO(await self.read())

    @contextlib.asynccontextmanager
    async def get(self):
        async with SESSION_CTX.get().get(self.url) as response:
            response.raise_for_status()
            yield response

    @override
    @contextlib.asynccontextmanager
    async def stream(self):
        async with self.get() as response:
            yield response.content

    @override
    async def json(self) -> t.Any:
        async with self.get() as response:
            return await response.json(content_type=None)


@attrs.define
class File(Resource):
    """A resource located on the local machine's storage."""

    path: pathlib.Path = attrs.field(converter=ensure_valid_path)
    """The path to the file."""

    if t.TYPE_CHECKING:
        def __init__(self, path: Pathish, /) -> None:
            ...

    @property
    @override
    def url(self) -> yarl.URL:
        return yarl.URL(f"attachment://{self.filename}")

    @property
    @override
    def filename(self) -> str:
        return self.path.name

    @override
    async def get_size(self) -> int:
        return self.path.stat().st_size

    @override
    async def read(self) -> bytes:
        with await self.open() as file:
            return file.read()

    @override
    async def open(self):
        return self.path.open("rb")

    @override
    @contextlib.asynccontextmanager
    async def stream(self):
        with await self.open() as file:
            yield file

    @override
    async def json(self) -> t.Any:
        with await self.open() as file:
            return orjson.loads(file.read())


@attrs.define
class Bytes(Resource):
    """An in-memory resource."""

    fp: io.BytesIO
    """The resource file object."""

    filename: str
    """Filename of the resource."""

    @property
    @override
    def url(self) -> yarl.URL:
        return yarl.URL(f"attachment://{self.filename}")

    @override
    async def get_size(self) -> int:
        return self.fp.getbuffer().nbytes

    @override
    async def read(self) -> bytes:
        return self.fp.getvalue()

    @override
    async def open(self):
        return self.fp

    @override
    @contextlib.asynccontextmanager
    async def stream(self):
        with self.fp as file:
            yield file

    @override
    async def json(self) -> t.Any:
        with self.fp as file:
            return orjson.loads(file.read())

    @classmethod
    def from_image(cls, image: Image, filename: str) -> Self:
        """Construct a Bytes resource from `Image` object."""
        try:
            ext = filename[filename.rindex(".") + 1:]
        except ValueError:
            raise ValueError("filename has no extension") from None

        fp = io.BytesIO()
        try:
            image.save(fp, format=ext)

        except KeyError:
            # PIL does not cleanly handle invalid formats and instead it just causes
            # a vague mapping lookup error when not found
            raise ValueError(f"Invalid file extension: {ext!r}") from None

        fp.seek(0)
        return cls(fp, filename)


if __name__ == "__main__":

    async def main():
        from PIL.Image import open

        async with aiohttp.ClientSession() as session:
            SESSION_CTX.set(session)

            res = URL("https://i.imgur.com/3jO2cXo.png")
            size = await res.get_size()
            print(f"The size of {res.url} is {size}B")
            image = open(await res.open())
            image.show(res.filename)

            res = File("D:/Obrazy/Games/SuperMechs/Sprites/Fanart/Deatomizer.png")
            size = await res.get_size()
            print(f"The size of {res.filename} is {size}B")
            image = open(await res.open())
            image.show(res.filename)

    import asyncio

    asyncio.run(main())
