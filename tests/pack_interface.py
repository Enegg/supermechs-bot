import logging

from SuperMechs import DEFAULT_PACK_URL, DEFAULT_PACK_V2_URL
from SuperMechs.pack_interface import PackInterface

logging.basicConfig(level=logging.DEBUG)

pack_v1_manager = PackInterface(DEFAULT_PACK_URL)
pack_v2_manager = PackInterface(DEFAULT_PACK_V2_URL)
local_manager = PackInterface("C:/Real_Shit_Estate/Item-packs/items.json")
