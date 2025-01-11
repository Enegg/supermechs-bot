from typing import Final

import attrs

from app.models.item_pack import ItemPack, PackKey


@attrs.define
class State:
    item_pack: ItemPack = ItemPack(key=PackKey("$not-loaded"))


state: Final = State()
