import logging
from collections import abc
from typing import Final

import disnake.abc

from app.models.ids import DiscordUserId, PlayerId
from app.models.player import Player

_LOG = logging.getLogger("managers")

PLAYER_MAPPING: Final[abc.Mapping[PlayerId, Player]] = {}
_discord_user_to_player_id: Final[abc.MutableMapping[DiscordUserId, PlayerId]] = {}


def find_player_by_user(user: disnake.abc.User, /) -> Player | None:
    player_id = _discord_user_to_player_id.get(DiscordUserId(user.id))

    if player_id is None:
        return None

    return PLAYER_MAPPING[player_id]


def get_or_create_player_from_user(user: disnake.abc.User, /) -> Player:
    user_id = DiscordUserId(user.id)

    if (existing_player_id := _discord_user_to_player_id.get(user_id)) is not None:
        return PLAYER_MAPPING[existing_player_id]

    player = PLAYER_MAPPING[player.id] = Player()
    _discord_user_to_player_id[user_id] = player.id
    _LOG.info("New player: id=%d, name=%s", player.id, user.name)
    return player
