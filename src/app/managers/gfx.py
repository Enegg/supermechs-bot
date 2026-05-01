import logging

from app.models.sprite_pack import AnySpritePack, DynamicSpritePack, SpriteKey, StaticSpritePack
from resources import HttpResource

_LOG = logging.getLogger("managers")
_sprite_pack: AnySpritePack = StaticSpritePack()


def get_sprite_pack() -> AnySpritePack:
    return _sprite_pack


def get_image_url(key: SpriteKey, /) -> str | None:
    match get_sprite_pack():
        case DynamicSpritePack() as pack:
            resource = pack.image_resources.get(key)

            if isinstance(resource, HttpResource):
                return resource.uri

            return None

        case _:
            return None


def store_sprite_pack(pack: AnySpritePack, /) -> None:
    global _sprite_pack

    match pack:
        case StaticSpritePack():
            image_count = len(pack.images)
            pack_type = "static"

        case DynamicSpritePack():
            image_count = len(pack.image_resources)
            pack_type = "dynamic"

    _LOG.info("Storing sprite pack: type=%s, images=%d", pack_type, image_count)
    _sprite_pack = pack
