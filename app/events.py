import typing as t

import anyio

BUFFS_LOADED: t.Final = anyio.Event()
PACK_LOADED: t.Final = anyio.Event()
