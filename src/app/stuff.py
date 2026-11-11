from collections import abc

from app import structs
from app.core.state import State
from resources import HttpResource

import supermechs.all as sm


def get_command_mention(name: str, /, state: State) -> str:
    mention = state.command_mentions.get(name)

    if mention is not None:
        return mention

    mention = state.command_mentions[name] = "/" + name
    return mention


def get_image_url(key: structs.SpriteKey, /, sprite_pack: structs.SpritePack) -> str | None:
    resource = sprite_pack.images.get(key)

    if isinstance(resource, HttpResource):
        return resource.uri

    return None


def filter_items(
    items: abc.Mapping[sm.Item.Id, sm.Item],
    /,
    slot: str | None = None,
    element: str | None = None,
    rarity: str | None = None,
) -> abc.Generator[sm.Item]:
    filters: list[abc.Callable[[sm.Item], bool]] = []

    if slot is not None:
        target_slot = sm.Item.Slot[slot]
        filters.append(lambda item: item.slot_id is target_slot)

    if element is not None:
        target_element = sm.Item.Element[element]
        filters.append(lambda item: item.element is target_element)

    if rarity is not None:
        min_tier = sm.Item.Rarity[rarity]
        filters.append(lambda item: item.stages[0].tier >= min_tier)

    if not filters:
        yield from items.values()
        return

    for item in items.values():
        if all(f(item) for f in filters):
            yield item
