from collections import abc

from resources import HttpResource

import dupermechs.all as sm

type SpriteKey = tuple[sm.Item.Id, sm.Item.Rarity]
type SpritePack = abc.Mapping[SpriteKey, HttpResource]
