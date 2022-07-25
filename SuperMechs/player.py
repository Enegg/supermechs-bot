from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from utils import MISSING, random_str

from .core import ArenaBuffs
from .inv_item import AnyInvItem
from .mech import Mech
from .types import WUSerialized


@dataclass
class Player:
    """Represents a SuperMechs player."""

    # TODO: add mech teams, and commands related to managing them

    id: int
    builds: dict[str, Mech] = field(default_factory=dict)
    arena_buffs: ArenaBuffs = field(default_factory=ArenaBuffs)
    inventory: dict[uuid.UUID, AnyInvItem] = field(default_factory=dict)
    active_build_name: str = MISSING
    level: int = 0
    exp: int = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def get_or_create_build(self, possible_name: str | None = None, /) -> Mech:
        """Retrieves active build if player has one, otherwise creates a new one.

        Parameters
        -----------
        possible_name:
            The name to create a new build with. Ignored if player has active build.
            If not passed, the name will be randomized.
        """
        if self.active_build_name is MISSING:
            return self.new_build(possible_name)

        return self.builds[self.active_build_name]

    @property
    def active_build(self) -> Mech | None:
        """Returns active build if player has one, `None` otherwise."""
        return self.builds.get(self.active_build_name)

    def new_build(self, name: str | None = None, /) -> Mech:
        """Creates a new build, sets it as active and returns it.

        Parameters
        -----------
        name:
            The name to assign to the build. If `None`, name will be randomized.
        """
        build = Mech()

        if name is None:
            while (name := random_str(6)) in self.builds:
                pass

        self.builds[name] = build
        self.active_build_name = name
        return build

    def rename(self, old_name: str, new_name: str) -> None:
        """Changes the name a build is assigned to.

        Parameters
        -----------
        old_name:
            Name of existing build to be changed.
        new_name:
            New name for the build.

        Raises
        -------
        ValueError
            Old name not found or new name already in use.
        """
        if old_name not in self.builds:
            raise ValueError("Build not found")

        if new_name in self.builds:
            raise ValueError("Provided name already present")

        self.builds[new_name] = self.builds.pop(old_name)

    def delete(self, name: str, /) -> None:
        """Deletes build from player's builds.

        Parameters
        -----------
        name:
            The name of the build to delete.

        Raises
        -------
        ValueError
            Name not found."""
        if name not in self.builds:
            raise ValueError("Build not found")

        del self.builds[name]

    def build_to_json(self, player_name: str, build_name: str | None = None) -> WUSerialized:
        """Parses a build to WU acceptable JSON format."""

        name = self.active_build_name or build_name

        if name is None:
            raise ValueError("Player has no active build and name was not passed.")

        build = self.builds.get(name)

        if build is None:
            raise TypeError(f"Player does not have a build {name}.")

        return build.wu_serialize(name, player_name)
