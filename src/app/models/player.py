import typing
import uuid
from collections import abc
from datetime import datetime

from attrs import define, field

from .mech_build import MechBuild

from disnake.utils import get as get_matching, utcnow

from supermechs.arenashop import ArenaShop, arena_shop
from supermechs.mech import Mech

__all__ = ("Player",)


@define
class Player:
    """Represents a SuperMechs player."""

    id: typing.Final[int] = field()
    builds: typing.Final[abc.MutableMapping[uuid.UUID, MechBuild]] = field(factory=dict)
    arena_shop: typing.Final[ArenaShop] = field(factory=arena_shop)
    created_at: typing.Final[datetime] = field(factory=utcnow)
    _recent_uuid: uuid.UUID | None = field(default=None, init=False)

    @property
    def recent_build(self) -> MechBuild | None:
        return None if self._recent_uuid is None else self.builds[self._recent_uuid]

    @recent_build.setter
    def recent_build(self, mech: MechBuild) -> None:
        if mech.id not in self.builds:
            msg = "Recent build set to a mech not belonging to the player"
            raise ValueError(msg)

        self._recent_uuid = mech.id

    def get_build_by_name(self, name: str, /) -> MechBuild | None:
        """Retrieve a build with given name."""
        return get_matching(self.builds.values(), name=name)

    def get_recent_or_create_build(self, possible_name: str | None = None, /) -> MechBuild:
        """Return recent build if the player has one, or create a new one.

        Parameters
        ----------
        possible_name: The name to create a new build with. Ignored if there's a recent build.
        """
        if (recent := self.recent_build) is not None:
            return recent

        return self.create_build(possible_name)

    def get_or_create_build(self, name: str, /) -> MechBuild:
        """Retrieves existing build under given name, otherwise creates a new one.

        Parameters
        ----------
        name: The name of the mech to get or create.
        """
        build = self.get_build_by_name(name)

        if build is not None:
            return build

        return self.create_build(name)

    def load_build(self, name: str, mech: Mech) -> None:
        build = MechBuild(mech, name)
        self.builds[build.id] = build

    def create_build(self, name: str | None = None, /) -> MechBuild:
        """Creates a new build, sets it as recent and returns it.

        Parameters
        ----------
        name: The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild() if name is None else MechBuild(name=name)
        self.builds[build.id] = build
        self._recent_uuid = build.id
        return build

    def rename_build(self, uuid: uuid.UUID, name: str) -> None:
        """Changes the name a build is assigned to.

        Parameters
        ----------
        name: The new name for the build.
        """
        self.builds[uuid].name = name

    def delete_build(self, uuid: uuid.UUID, /) -> None:
        """Deletes a build from player's builds.

        Parameters
        ----------
        uuid: The uuid of the build to delete.
        """
        try:
            del self.builds[uuid]

        except KeyError:
            msg = f"No build with uuid {uuid}"
            raise LookupError(msg) from None
