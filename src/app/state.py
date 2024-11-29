import asyncio
from typing import Final
from typing_extensions import override

import aiohttp
import attrs

from app.models.item_pack import ItemPack, PackKey


class _NullEventLoop(asyncio.AbstractEventLoop):
    @override
    def get_debug(self) -> bool:
        return False


@attrs.define
class State:
    # perhaps turn it into a property
    http_session: aiohttp.ClientSession = aiohttp.ClientSession(loop=_NullEventLoop())
    item_pack: ItemPack = ItemPack(key=PackKey("$not-loaded"))


state: Final = State()
