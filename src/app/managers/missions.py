import enum
from collections import abc

import msgspec
import rich

from app import paths


class TeamSize(enum.Enum):
    _1v1 = "1v1"
    _2v2 = "2v2"
    _3v3 = "3v3"


class BoxReward(enum.Enum):
    none = "none"
    standard = "normal"
    fortune = "fortune"


class MissionType(enum.Enum):
    normal = "normal"
    side = "side_mission"
    portal = "portal"


class MissionEnemyDto(msgspec.Struct, kw_only=True):
    count: int
    element: str


class MissionEnemiesDto(msgspec.Struct, kw_only=True):
    buggy: MissionEnemyDto | msgspec.UnsetType = msgspec.UNSET
    tank: MissionEnemyDto | msgspec.UnsetType = msgspec.UNSET
    mech: MissionEnemyDto | msgspec.UnsetType = msgspec.UNSET


class MissionBossDto(msgspec.Struct, kw_only=True):
    name: str
    element: str


class MissionDiffDto(msgspec.Struct, kw_only=True):
    fuel_cost: int
    coins: int
    exp: int
    tickets: int = 0
    first_clear_tokens: int = 0


class MissionDto(msgspec.Struct, kw_only=True):
    id: str
    level: int
    type: MissionType = MissionType.normal
    mode: TeamSize
    chapter: str
    box: BoxReward = BoxReward.none
    boss: MissionBossDto | msgspec.UnsetType = msgspec.UNSET
    structures: int = 0
    pickups: int = 0
    enemies: MissionEnemiesDto
    diff_normal: MissionDiffDto
    diff_hard: MissionDiffDto
    diff_insane: MissionDiffDto


class MissionsFileDto(msgspec.Struct):
    version: str
    missions: abc.Sequence[MissionDto]


missions = msgspec.toml.decode(paths.MISSIONS_TOML.read_bytes(), type=MissionsFileDto).missions

if __name__ == "__main__":
    rich.print(missions[-2])
