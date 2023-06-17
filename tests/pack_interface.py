import logging
import typing as t

from app.shared import SESSION_CTX

from files import URL

from supermechs.item_pack import ItemPack
from supermechs.urls import PACK_V2

logging.basicConfig(level=logging.DEBUG)


async def runner(link: str = PACK_V2, **extra: t.Any):
    from aiohttp import ClientSession

    # import yarl

    logging.basicConfig(level="INFO")
    async with ClientSession() as session:
        SESSION_CTX.set(session)
        interface = ItemPack.from_json(await URL(link).json())
        return interface
