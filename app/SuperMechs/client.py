from __future__ import annotations

import logging

from abstract.files import URL

from . import urls
from .pack_interface import ItemPack
from .state import AppState
from .utils import MISSING

__all__ = ("SMClient",)

LOGGER = logging.getLogger(__name__)


class SMClient:
    """Represents the SuperMechs app."""

    default_pack: ItemPack

    def __init__(self) -> None:
        self.state = AppState()
        self.default_pack = MISSING

    async def fetch_default_item_pack(self) -> None:
        resource = URL(urls.PACK_V2)
        data = await resource.json()
        try:
            pack = self.state.store_item_pack(data, False)

        except Exception as err:
            LOGGER.warning("Failed to load default pack: ", exc_info=err)

        else:
            self.default_pack = pack
