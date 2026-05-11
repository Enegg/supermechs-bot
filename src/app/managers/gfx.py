import logging

from app.models.sprite_pack import SpriteKey, SpritePack
from resources import HttpResource

_LOG = logging.getLogger("managers")
_sprite_store: SpritePack = {}


def get_image_url(key: SpriteKey, /) -> str | None:
    resource = _sprite_store.get(key)

    if isinstance(resource, HttpResource):
        return resource.uri

    return None


def set_sprite_pack(pack: SpritePack, /) -> None:
    global _sprite_store
    _LOG.info("Storing sprite pack: images=%d", len(pack))
    _sprite_store = pack
