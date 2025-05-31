from collections import abc
from datetime import datetime
from typing import Final

import attrs

from app import snowflake
from app.class_utils import limited_repr
from app.models.item import Item
from app.utils import utcnow

from .ids import BuildId, PlayerId
from .mech_build import MechBuild

import dupermechs.all as sm

__all__ = ("Player",)


@attrs.define
class Player:
    """Represents a SuperMechs player."""

    id: Final[PlayerId] = attrs.field(factory=snowflake.new[PlayerId])
    builds: Final[dict[BuildId, MechBuild]] = attrs.field(factory=dict, repr=limited_repr)
    arena_shop: Final[sm.ArenaShop[int]] = attrs.field(factory=sm.ArenaShop.zero, repr=limited_repr)
    created_at: Final[datetime] = attrs.field(factory=utcnow)
    _recent_build_id: BuildId = attrs.field(default=BuildId(snowflake.NIL), init=False)

    @property
    def recent_build(self) -> MechBuild | None:
        return self.builds.get(self._recent_build_id)

    @recent_build.setter
    def recent_build(self, mech: MechBuild) -> None:
        assert mech.id in self.builds
        self._recent_build_id = mech.id

    def has_builds(self) -> bool:
        return bool(self.builds)

    def load_build(self, name: str, mech: sm.Mech[Item]) -> None:
        build = MechBuild(mech=mech, name=name)
        self.builds[build.id] = build

    def create_build(self, name: str | None = None, /) -> MechBuild:
        """Create, set as recent, and return a new build.

        Parameters
        ----------
        name:
            The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild(mech=sm.Mech()) if name is None else MechBuild(name=name, mech=sm.Mech())

        self.builds[build.id] = build
        self._recent_build_id = build.id
        return build

    def rename_build(self, uuid: BuildId, name: str) -> None:
        """Change the name a build is assigned to.

        Parameters
        ----------
        name: The new name for the build.
        """
        self.builds[uuid].name = name

    def iter_builds(self) -> abc.Iterator[MechBuild]:
        yield from self.builds.values()
