import typing

import anyio

BUFFS_LOADED: typing.Final = anyio.Event()
DEFAULT_PACK_LOADED: typing.Final = anyio.Event()
