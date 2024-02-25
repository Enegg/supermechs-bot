import typing

import anyio

BUFFS_LOADED: typing.Final = anyio.Event()
PACK_LOADED: typing.Final = anyio.Event()
