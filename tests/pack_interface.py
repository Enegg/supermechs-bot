import logging
import typing as t

from abstract.files import URL
from shared import SESSION_CTX
from SuperMechs.pack_interface import PackInterface
from SuperMechs.urls import PACK_V2_URL

logging.basicConfig(level=logging.DEBUG)

# pack_v1_manager = PackInterface(DEFAULT_PACK_URL)
# pack_v2_manager = PackInterface(DEFAULT_PACK_V2_URL)
# local_manager = PackInterface("C:/Real_Shit_Estate/Item-packs/items.json")

async def runner(link: str=PACK_V2_URL, **extra: t.Any):
    from aiohttp import ClientSession

    # import yarl

    logging.basicConfig(level="INFO")
    interface = PackInterface()
    async with ClientSession() as session:
        SESSION_CTX.set(session)
        resource = URL(link)
        await interface.load(resource, **extra)
        return interface
