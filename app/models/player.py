import uuid
from collections import abc

import disnake
from attrs import define, field

from .mech_build import MechBuild

from supermechs.arenashop import ArenaShop, arena_shop
from supermechs.mech import Mech

__all__ = ("Player",)


@define
class Player:
    """Represents a SuperMechs player."""

    user: disnake.abc.User = field()
    builds: abc.MutableMapping[uuid.UUID, MechBuild] = field(factory=dict)
    arena_shop: ArenaShop = field(factory=arena_shop, init=False)
    _active_build: MechBuild | None = field(default=None, init=False)

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def active_build(self) -> MechBuild | None:
        return self._active_build

    @active_build.setter
    def active_build(self, mech: MechBuild) -> None:
        if mech.id not in self.builds:
            msg = "Active build set to a mech not belonging to the player"
            raise ValueError(msg)

        self._active_build = mech

    def get_build_by_name(self, name: str, /) -> MechBuild | None:
        """Retrieve a build with given name."""
        for build in self.builds.values():
            if build.name == name:
                return build

        return None

    def get_active_or_create_build(self, possible_name: str | None = None, /) -> MechBuild:
        """Retrieves active build if the player has one, otherwise creates a new one.

        Parameters
        ----------
        possible_name: The name to create a new build with. Ignored if there's an active build.
        """
        if self.active_build is None:
            return self.create_build(possible_name)

        return self.active_build

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

    def create_build(self, name: str | None = None, /, mech: Mech | None = None) -> MechBuild:
        """Creates a new build, sets it as active and returns it.

        Parameters
        ----------
        name: The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild() if name is None else MechBuild(name=name)
        self.builds[build.id] = self._active_build = build
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
