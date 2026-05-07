import logging

from app.core import AppState
from app.models.sprite_pack import SpriteKey, SpritePack
from resources import HttpResource

_LOG = logging.getLogger("managers")


def get_image_url(key: SpriteKey, /) -> str | None:
    resource = AppState.sprite_pack.get(key)

    if isinstance(resource, HttpResource):
        return resource.uri

    return None


def set_sprite_pack(pack: SpritePack, /) -> None:
    _LOG.info("Storing sprite pack: images=%d", len(pack))
    AppState.sprite_pack = pack
