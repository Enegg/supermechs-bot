from datetime import datetime
from typing import Final, NewType, Self

from attrs import define, field

import disnake
from disnake.utils import get as get_matching, utcnow

from app.class_utils import limited_repr

from .mech_build import BuildId, MechBuild

from supermechs.arenashop import ArenaShop, arena_shop
from supermechs.mech import Mech

__all__ = ("Player", "PlayerId")

PlayerId = NewType("PlayerId", int)


@define
class Player:
    """Represents a SuperMechs player."""

    id: Final[PlayerId]
    builds: Final[dict[BuildId, MechBuild]] = field(factory=dict)
    arena_shop: Final[ArenaShop] = field(factory=arena_shop, repr=limited_repr)
    created_at: Final[datetime] = field(factory=utcnow)
    _recent_build_id: BuildId | None = field(default=None, init=False)

    @property
    def recent_build(self) -> MechBuild | None:
        return None if self._recent_build_id is None else self.builds[self._recent_build_id]

    @recent_build.setter
    def recent_build(self, mech: MechBuild) -> None:
        if mech.id not in self.builds:
            msg = "Recent build set to a mech not belonging to the player"
            raise ValueError(msg)

        self._recent_build_id = mech.id

    def get_build_by_name(self, name: str, /) -> MechBuild | None:
        """Retrieve a build with given name."""
        return get_matching(self.builds.values(), name=name)

    def get_recent_or_create_build(self, possible_name: str | None = None, /) -> MechBuild:
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
        build = self.get_build_by_name(name)

        if build is not None:
            return build

        return self.create_build(name)

    def load_build(self, name: str, mech: Mech) -> None:
        build = MechBuild(mech=mech, name=name)
        self.builds[build.id] = build

    def create_build(self, name: str | None = None, /) -> MechBuild:
        """Create, set as recent, and return a new build.

        Parameters
        ----------
        name:
            The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild() if name is None else MechBuild(name=name)
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

    @classmethod
    def from_user(cls, user: disnake.abc.User, /) -> Self:
        return cls(id=PlayerId(user.id))
