from collections import abc

import msgspec

from dupermechs.arenashop import ArenaShop


class FlatBuffDto(msgspec.Struct, tag_field="type", tag="+"):
    values: abc.Sequence[int]


class PercentBuffDto(msgspec.Struct, tag_field="type", tag="%"):
    values: abc.Sequence[int]


type AnyBuffDto = FlatBuffDto | PercentBuffDto
type ArenaBuffsDto = ArenaShop[AnyBuffDto]
