import logging
import typing as t

from .pack_interface import ItemPack, extract_info
from .player import Player
from .typedefs import AnyItemPack

LOGGER = logging.getLogger(__name__)


@t.runtime_checkable
class UserLike(t.Protocol):
    @property
    def id(self) -> int:
        ...

    @property
    def name(self) -> str:
        ...


class AppState:
    """Object responsible for keeping track of cache-able objects."""

    _players: dict[int, Player]
    _packs: dict[str, ItemPack]

    def create_player(self, user: UserLike) -> Player:
        LOGGER.info(f"New player created: {user.id} ({user.name})")
        return Player(id=user.id, name=user.name)

    def store_player(self, user: UserLike) -> Player:
        try:
            return self._players[user.id]

        except KeyError:
            player = self.create_player(user)
            self._players[user.id] = player
            return player

    def get_player(self, id: int) -> Player:
        return self._players[id]

    def has_player(self, id: int) -> bool:
        return id in self._players

    def create_item_pack(self, data: AnyItemPack, custom: bool = False) -> ItemPack:
        pack = ItemPack.from_json(data, custom=custom)
        LOGGER.info(f"Item pack created: {pack.key} ({pack.name})")
        return pack

    def store_item_pack(self, data: AnyItemPack, custom: bool = False) -> ItemPack:
        key = extract_info(data).key
        try:
            return self._packs[key]

        except KeyError:
            pack = self.create_item_pack(data, custom)
            self._packs[key] = pack
            return pack

    def get_item_pack(self, key: str) -> ItemPack:
        return self._packs[key]

    def has_item_pack(self, key: str) -> bool:
        return key in self._packs
