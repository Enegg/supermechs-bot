from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import typing as t

import aiohttp
import attrs
import yarl
from typing_extensions import Self

from shared import SESSION_CTX
from typeshed import T

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


class Resource(t.Generic[T]):
    """Base for any uploadable or downloadable representation of information."""

    __slots__ = ()
    _registered_type: t.ClassVar[type] = type(None)
    _registry: t.ClassVar[dict[type, type[Self]]] = {}

    @property
    def url(self) -> Urlish:
        """URL of the resource."""
        raise NotImplementedError

    @property
    def filename(self) -> str:
        """Filename of the resource."""
        raise NotImplementedError

    async def get_size(self) -> int | None:
        """Get the size of the resource, in bytes, if possible."""
        return None

    def __new__(cls, arg: T, /, *args: t.Any, **kwargs: t.Any) -> Self:
        if cls is not Resource:
            return object.__new__(cls)

        for bound_type, subclass in cls._registry.items():
            if isinstance(arg, bound_type):
                return object.__new__(subclass)

        else:
            raise ValueError(f"No valid resource handler for {type(arg)} registered")

    def __init_subclass__(cls, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        # __init_subclass__ will be called twice due to attrs reconstructing a slotted class
        cls._registry[cls._registered_type] = cls

    def __class_getitem__(cls, param: type[T]) -> type[Self]:
        cls._registered_type = param
        return super().__class_getitem__(param)  # type: ignore

    def __repr__(self) -> str:
        return f"{type(self).__name__}(url={self.url!r}, filename={self.filename!r})"

    @property
    def extension(self) -> str | None:
        """File extension, if there is one."""
        _, ext = os.path.splitext(self.filename)
        return ext or None

    async def read(self) -> bytes:
        """Read the data of the resource, all at once."""
        raise NotImplementedError

    async def open(self) -> io.BufferedIOBase:
        """Get a (possibly arbitrary) file pointer for the resource. Remember to close the file afterwards."""
        raise NotImplementedError

    def stream(self) -> contextlib.AbstractAsyncContextManager[t.Any]:
        """Stream context manager for the resource."""
        raise NotImplementedError

    def json(self) -> t.Any:
        """Get the contents of the resource loaded as json."""
        raise NotImplementedError


@attrs.define
class URL(Resource[yarl.URL]):
    """A URL that represents a web resource."""

    url: Urlish = attrs.field(converter=ensure_valid_url)
    """URL of the resource."""

    @property
    def filename(self) -> str:
        return os.path.basename(t.cast(yarl.URL, self.url).path)

    async def get_size(self) -> int | None:
        async with SESSION_CTX.get().head(self.url) as response:
            return webresource_size(response)

    async def read(self) -> bytes:
        async with self.stream() as stream:
            return await stream.read()

    async def open(self) -> io.BytesIO:
        return io.BytesIO(await self.read())

    @contextlib.asynccontextmanager
    async def get(self):
        async with SESSION_CTX.get().get(self.url) as response:
            response.raise_for_status()
            yield response

    @contextlib.asynccontextmanager
    async def stream(self):
        async with self.get() as response:
            yield response.content

    async def json(self) -> t.Any:
        async with self.get() as response:
            return await response.json(content_type=None)


@attrs.define
class File(Resource[pathlib.Path]):
    """A resource located on the local machine's storage."""

    path: pathlib.Path = attrs.field(converter=ensure_valid_path)
    """The path to the file."""

    @property
    def url(self) -> yarl.URL:
        return yarl.URL(f"attachment://{self.filename}")

    @property
    def filename(self) -> str:
        return self.path.name

    async def get_size(self) -> int:
        return self.path.stat().st_size

    async def read(self) -> bytes:
        with await self.open() as file:
            return file.read()

    async def open(self):
        return self.path.open("rb")

    @contextlib.asynccontextmanager
    async def stream(self):
        with await self.open() as file:
            yield file

    async def json(self) -> t.Any:
        with await self.open() as file:
            return json.load(file)


@attrs.define
class Bytes(Resource[io.BytesIO]):
    """An in-memory resource."""

    fp: io.BytesIO
    """The resource file object."""

    filename: str
    """The name for the resource."""

    @property
    def url(self) -> yarl.URL:
        return yarl.URL(f"attachment://{self.filename}")

    async def get_size(self) -> int | None:
        return self.fp.getbuffer().nbytes

    async def read(self) -> bytes:
        return self.fp.getvalue()

    async def open(self):
        return self.fp

    @contextlib.asynccontextmanager
    async def stream(self):
        with self.fp as file:
            yield file

    async def json(self) -> t.Any:
        with self.fp as file:
            return json.load(file)

    @classmethod
    def from_image(cls, image: Image, filename: str) -> Self:
        """Construct a Bytes resource from `Image` object."""
        fp = io.BytesIO()

        _, ext = os.path.splitext(filename)
        image.save(fp, format=ext)
        fp.seek(0)

        return cls(fp, filename)


if __name__ == "__main__":

    async def main():
        from PIL.Image import open

        async with aiohttp.ClientSession() as session:
            SESSION_CTX.set(session)

            res = Resource(yarl.URL("https://i.imgur.com/3jO2cXo.png"))
            size = await res.get_size()
            print(f"The size of {res.url} is {size}B")

            res = Resource(pathlib.Path("D:/Obrazy/Games/SuperMechs/Sprites/Fanart/Deatomizer.png"))
            size = await res.get_size()
            print(f"The size of {res.filename} is {size}B")

            # test direct instances
            res = URL(yarl.URL("https://i.imgur.com/3jO2cXo.png"))
            image = open(io.BytesIO(await res.read()))
            image.show(res.filename)

            res = File(pathlib.Path("D:/Obrazy/Games/SuperMechs/Sprites/Fanart/Deatomizer.png"))
            image = open(io.BytesIO(await res.read()))
            image.show(res.filename)

    import asyncio

    asyncio.run(main())
