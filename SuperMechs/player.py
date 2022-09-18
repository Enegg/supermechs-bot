from __future__ import annotations

import uuid

from attrs import Factory, define

from .core import ArenaBuffs
from .inv_item import AnyInvItem
from .mech import Mech
from .utils import MISSING, truncate_name


@define
class Player:
    """Represents a SuperMechs player."""

    # TODO: add mech teams, and methods related to managing them

    id: int
    name: str
    builds: dict[str, Mech] = Factory(dict)
    teams: dict[str, list[Mech]] = Factory(dict)
    arena_buffs: ArenaBuffs = Factory(ArenaBuffs)
    inventory: dict[uuid.UUID, AnyInvItem] = Factory(dict)
    active_build_name: str = MISSING
    active_team_name: str = MISSING
    level: int = 0
    exp: int = 0

    def get_or_create_active_build(self, possible_name: str | None = None, /) -> Mech:
        """Retrieves active build if the player has one, otherwise creates a new one.

        Parameters
        ----------
        possible_name: The name to create a new build with. Ignored if the player has an active build.
        """
        if self.active_build_name is MISSING:
            return self.create_build(possible_name)

        return self.builds[self.active_build_name]

    def get_active_build(self) -> Mech | None:
        """Returns active build if the player has one, `None` otherwise."""
        return self.builds.get(self.active_build_name)

    def create_build(self, name: str | None = None, /) -> Mech:
        """Creates a new build, sets it as active and returns it.

        Parameters
        -----------
        name:
            The name to assign to the build. If `None`, name will be `"Unnamed Mech <n>"`.
        """

        if name is None:
            n = 1
            while (name := f"Unnamed Mech {n}") in self.builds:
                n += 1

        else:
            name = truncate_name(name)

        build = Mech(name=name)
        self.builds[name] = build
        self.active_build_name = name
        return build

    def rename_build(self, old_name: str, new_name: str, *, overwrite: bool = False) -> None:
        """Changes the name a build is assigned to.

        Parameters
        ----------
        old_name: The name of an existing build to be changed.
        new_name: A new name for the build.
        """
        if old_name not in self.builds:
            raise ValueError("Build not found")

        new_name = truncate_name(new_name)

        if new_name in self.builds and not overwrite:
            raise ValueError("Provided name is already in use")

        self.builds[new_name] = self.builds.pop(old_name)

    def delete_build(self, name: str, /) -> None:
        """Deletes build from player's builds.

        Parameters
        ----------
        name: The name of the build to delete.
        """
        if name not in self.builds:
            raise ValueError("Build not found")

        del self.builds[name]
