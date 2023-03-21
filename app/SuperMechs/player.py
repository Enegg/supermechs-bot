from __future__ import annotations

from attrs import define, field

from .core import ArenaBuffs
from .mech import Mech
from .utils import truncate_name

__all__ = ("Player",)


@define
class Player:
    """Represents a SuperMechs player."""

    id: int
    name: str
    builds: dict[str, Mech] = field(factory=dict, init=False)
    arena_buffs: ArenaBuffs = field(factory=ArenaBuffs, init=False)
    _active_build: Mech | None = field(default=None, init=False)
    # inventory: dict[uuid.UUID, AnyInvItem] = Factory(dict)
    # teams: dict[str, list[Mech]] = Factory(dict)
    # active_team_name: str = MISSING
    # level: int = 0
    # exp: int = 0

    @property
    def active_build(self) -> Mech | None:
        return self._active_build

    @active_build.setter
    def active_build(self, mech: Mech) -> None:
        if mech.name not in self.builds:
            raise ValueError("Active build set to a mech not belonging to the player")

        self._active_build = mech

    def get_active_or_create_build(self, possible_name: str | None = None, /) -> Mech:
        """Retrieves active build if the player has one, otherwise creates a new one.

        Parameters
        ----------
        possible_name:
            The name to create a new build with.
            Ignored if the player has an active build.
        """
        if self.active_build is None:
            return self.create_build(possible_name)

        return self.active_build

    def get_or_create_build(self, name: str, /) -> Mech:
        """Retrieves existing build under given name, otherwise creates a new one.

        Parameters
        ----------
        name: The name of the mech to get or create.
        """
        if name in self.builds:
            return self.builds[name]

        return self.create_build(name)

    def create_build(self, name: str | None = None, /) -> Mech:
        """Creates a new build, sets it as active and returns it.

        Parameters
        ----------
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
        self.builds[name] = self._active_build = build
        return build

    def rename_build(self, old_name: str, new_name: str, *, overwrite: bool = False) -> None:
        """Changes the name a build is assigned to.

        Parameters
        ----------
        old_name: The name of an existing build to be changed.

        new_name: A new name for the build.
        """
        if old_name not in self.builds:
            raise ValueError(f"No build named {old_name!r}")

        new_name = truncate_name(new_name)

        if new_name in self.builds and not overwrite:
            raise ValueError("Provided name is already in use")

        mech = self.builds[new_name] = self.builds.pop(old_name)
        mech.name = new_name

    def delete_build(self, name: str, /) -> None:
        """Deletes build from player's builds.

        Parameters
        ----------
        name: The name of the build to delete.
        """
        try:
            del self.builds[name]

        except KeyError:
            raise ValueError(f"No build named {name!r}") from None
