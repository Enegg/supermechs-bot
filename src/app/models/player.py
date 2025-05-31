from collections import abc
from datetime import datetime
from typing import Final

import attrs
from monads.option import Null, Option, Some

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

    def find_build_by_name(self, name: str, /) -> MechBuild | None:
        """Retrieve a build with given name."""

        def predicate(build_name: str) -> bool:
            return build_name == name

        for build in self.builds.values():
            if build.name.is_some_and(predicate):
                return build

        return None

    def has_builds(self) -> bool:
        return bool(self.builds)

    def get_recent_or_create_build(self, possible_name: Option[str] = Null.null, /) -> MechBuild:
        """Return recent build if the player has one, or create a new one.

        Parameters
        ----------
        possible_name:
            The name to create a new build with. Ignored if there's a recent build.
        """
        if (recent := self.recent_build) is not None:
            return recent

        return self.create_build(possible_name)

    def get_or_create_build(self, name: str, /) -> MechBuild:
        """Retrieve existing build under given name, otherwise create a new one.

        Parameters
        ----------
        name:
            The name of the mech to get or create.
        """
        build = self.find_build_by_name(name)

        if build is not None:
            return build

        return self.create_build(Some(name))

    def load_build(self, name: str, mech: sm.Mech[Item]) -> None:
        build = MechBuild(mech=mech, name=Some(name))
        self.builds[build.id] = build

    def create_build(self, name: Option[str] = Null.null, /) -> MechBuild:
        """Create, set as recent, and return a new build.

        Parameters
        ----------
        name:
            The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild(name=name, mech=sm.Mech())
        self.builds[build.id] = build
        self._recent_build_id = build.id
        return build

    def rename_build(self, uuid: BuildId, name: str) -> None:
        """Change the name a build is assigned to.

        Parameters
        ----------
        name: The new name for the build.
        """
        self.builds[uuid].name = Some(name)

    def delete_build(self, id: BuildId, /) -> None:
        """Delete a build from player's builds.

        Parameters
        ----------
        id:
            The id of the build to delete.
        """
        try:
            del self.builds[id]

        except KeyError:
            msg = f"No build with ID {id}"
            raise LookupError(msg) from None

    def iter_builds(self) -> abc.Iterator[MechBuild]:
        yield from self.builds.values()
