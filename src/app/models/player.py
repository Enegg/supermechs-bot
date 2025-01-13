from collections import abc
from datetime import datetime
from typing import Final, NewType, Self

import attrs
from monads.option import Null, Option, Some

import disnake

from app.class_utils import limited_repr
from app.models.item_pack import ItemPack
from app.utils import utcnow

from .mech_build import BuildId, MechBuild, PartialMechBuild

from supermechs.item import Item

# from supermechs.arenashop import ArenaShop, arena_shop
from supermechs.mech import Mech

__all__ = ("PartialPlayer", "Player", "PlayerId")

PlayerId = NewType("PlayerId", int)


@attrs.define(kw_only=True, frozen=True)
class PartialPlayer:
    id: PlayerId
    builds: abc.Sequence[PartialMechBuild]
    arena_shop: abc.Mapping[str, int]
    created_at: datetime
    recent_build_id: BuildId | None

    def as_complete(self, pack: ItemPack, /) -> "Player":
        builds: dict[BuildId, MechBuild] = {}

        for partial_build in self.builds:
            build = partial_build.as_complete(pack)
            builds[build.id] = build

        return Player(
            id=self.id,
            builds=builds,
            arena_shop=dict(self.arena_shop),
            created_at=self.created_at,
        )


@attrs.define
class Player:
    """Represents a SuperMechs player."""

    id: Final[PlayerId]
    builds: Final[dict[BuildId, MechBuild]] = attrs.field(factory=dict, repr=limited_repr)
    arena_shop: Final[dict[str, int]] = attrs.field(factory=dict, repr=limited_repr)
    created_at: Final[datetime] = attrs.field(factory=utcnow)
    _recent_build_id: BuildId | None = attrs.field(default=None, init=False)

    @property
    def recent_build(self) -> MechBuild | None:
        return None if self._recent_build_id is None else self.builds[self._recent_build_id]

    @recent_build.setter
    def recent_build(self, mech: MechBuild) -> None:
        if mech.id not in self.builds:
            msg = "Recent build set to a mech not belonging to the player"
            raise ValueError(msg)

        self._recent_build_id = mech.id

    def as_partial(self) -> PartialPlayer:
        return PartialPlayer(
            id=self.id,
            builds=[build.as_partial() for build in self.builds.values()],
            arena_shop=self.arena_shop.copy(),
            created_at=self.created_at,
            recent_build_id=self._recent_build_id,
        )

    def get_build_by_name(self, name: str, /) -> MechBuild | None:
        """Retrieve a build with given name."""
        for build in self.builds.values():
            if build.name.is_some_and(lambda s: s == name):
                return build

        return None

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
        build = self.get_build_by_name(name)

        if build is not None:
            return build

        return self.create_build(Some(name))

    def load_build(self, name: str, mech: Mech[Item]) -> None:
        build = MechBuild(mech=mech, name=Some(name))
        self.builds[build.id] = build

    def create_build(self, name: Option[str] = Null.null, /) -> MechBuild:
        """Create, set as recent, and return a new build.

        Parameters
        ----------
        name:
            The name to assign to the build. Defaults to `"Unnamed Mech"`.
        """
        build = MechBuild(name=name, mech=Mech())
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

    @classmethod
    def from_user(cls, user: disnake.abc.User, /) -> Self:
        return cls(id=PlayerId(user.id))
