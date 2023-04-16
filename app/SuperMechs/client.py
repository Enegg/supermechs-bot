from __future__ import annotations

import logging

from files import URL

from . import urls
from .pack_interface import ItemPack
from .rendering import PackRenderer
from .state import AppState
from .utils import MISSING

__all__ = ("SMClient",)

LOGGER = logging.getLogger(__name__)


class SMClient:
    """Represents the SuperMechs app."""

    default_pack: ItemPack
    default_renderer: PackRenderer

    def __init__(self) -> None:
        self.state = AppState()
        self.default_pack = MISSING

    async def fetch_default_item_pack(self) -> None:
        """Downloads & parses the default item pack."""
        resource = URL(urls.PACK_V2)
        data = await resource.json()
        self.default_pack = self.state.store_item_pack(data, False)
        self.default_renderer = self.state.store_pack_renderer(data)
        await self.default_renderer.load(data)

    def get_default_renderer(self) -> PackRenderer:
        return self.state.get_pack_renderer(self.default_pack.key)
