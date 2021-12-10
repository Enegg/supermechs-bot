from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from typing import *

import aiohttp

from enums import STAT_NAMES, WORKSHOP_STATS, Elements, Icons, Rarity
from functions import js_format, random_str
from image_manipulation import MechRenderer, get_image, get_image_w_h

if TYPE_CHECKING:
    from PIL.Image import Image
    from typing_extensions import NotRequired

    class PackConfig(TypedDict):
        key: str
        name: str
        base_url: str
        description: str


AnyType = Literal['TORSO', 'LEGS', 'DRONE', 'SIDE_WEAPON', 'TOP_WEAPON', 'TELEPORTER', 'CHARGE_ENGINE', 'GRAPPLING_HOOK', 'MODULE']
AnyElement = Literal['PHYSICAL', 'EXPLOSIVE', 'ELECTRIC', 'COMBINED']

# TORSO, LEGS, DRONE, SIDE_WEAPON, TOP_WEAPON, TELEPORTER, CHARGE, GRAPPLING_HOOK, MODULE

ItemType = TypeVar('ItemType', bound=AnyType)


class AnyStats(TypedDict, total=False):
    # NOTE: entries typed as tuples are actually lists, since they come from a JSON
    # but we type it as tuples since they have fixed size and that matters more
    # it could cause bugs had the actual lists be mutated, but unless you know it's actually a list,
    # why would you attempt to mutate something typed as tuple?
    # extra precaution: tuples can be hashed, allowing them as keys for dicts etc, whereas lists cannot
    # but using a damage range as dict key does not sound reasonable
    weight: int
    health: int
    eneCap: int
    eneReg: int
    heaCap: int
    heaCol: int
    bulletCap: int
    rocketCap: int
    phyRes: int
    expRes: int
    eleRes: int
    phyDmg: tuple[int, int]
    phyResDmg: int
    eleDmg: tuple[int, int]
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: tuple[int, int]
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    walk: int
    jump: int
    range: tuple[int, int]
    push: int
    pull: int
    recoil: int
    advance: int
    retreat: int
    uses: int
    backfire: int
    heaCost: int
    eneCost: int
    bulletCost: int
    rocketCost: int


class Attachment(TypedDict):
    x: int
    y: int

Attachments = dict[str, Attachment]
AnyAttachment = Union[Attachment, Attachments, None]

class ItemPack(TypedDict):
    config: PackConfig
    items: list[ItemDict]


class ItemDict(TypedDict):
    id: int
    name: str
    image: str
    width:  NotRequired[int]
    height: NotRequired[int]
    type: AnyType
    element: AnyElement
    transform_range: str
    stats:  AnyStats
    divine: AnyStats
    tags: NotRequired[list[str]]
    attachment: NotRequired[Attachment | Attachments]


AttachmentType = TypeVar('AttachmentType', bound=AnyAttachment)


class Item(Generic[AttachmentType]):
    """Represents a single item."""
    def __init__(
        self,
        *,
        id: int,
        name: str,
        image: str,
        type: str,
        stats: AnyStats,
        transform_range: str,
        pack: PackConfig,
        divine: AnyStats | None = None,
        element: str = 'OMNI',
        attachment: AttachmentType = cast(AttachmentType, None),
        **kwargs: Any
    ) -> None:

        self.id = id
        self.name = str(name)

        self.image_url = js_format(str(image), url=pack['base_url'])
        self.pack = pack
        self._image: Image | None = None

        self.icon = Icons[type]  # this will also validate if type is of correct type
        self.stats = stats
        self.divine = divine

        val_a, _, val_b = transform_range.partition('-')
        self.rarity = (Rarity[val_a], Rarity[val_b]) if val_b else Rarity[val_a]
        self.element = Elements[element]

        self.attachment = attachment
        self.kwargs = kwargs


    def __str__(self) -> str:
        return self.name


    def __repr__(self) -> str:
        return f'<Item {self.name!r}: element={self.element.name} type={self.type} {self.rarity=} {self.stats=}>'


    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Item):
            return False

        return (o.id     == self.id
            and o.image_url == self.image_url
            and o.name   == self.name
            and o.type   == self.type
            and o.stats  == self.stats
            and o.divine == self.divine
            and o.rarity == self.rarity)


    def __hash__(self) -> int:
        return hash((self.id, self.name, self.type, self.rarity, self.element, self.pack['key']))


    @property
    def type(self) -> AnyType:
        return cast(AnyType, self.icon.name)


    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.type not in {'TELEPORTER', 'CHARGE', 'HOOK', 'MODULE'}


    @property
    def image(self) -> Image:
        """Returns a copy of image for this item. Before this property is ever retrieved, load_image needs to be called."""
        if self._image is None:
            raise RuntimeError('load_image was never called')

        if 'width' in self.kwargs or 'height' in self.kwargs:
            new_width  = self.kwargs.get('width',  0)
            new_height = self.kwargs.get('height', 0)

            width, height = get_image_w_h(self._image)
            width = new_width or width
            height = new_height or height

            return self._image.resize((width, height))

        return self._image.copy()


    async def load_image(self, session: aiohttp.ClientSession) -> None:
        """Loads the image from web"""
        if self.image_url is None:
            raise ValueError('Image URL was not set')

        self._image = await get_image(self.image_url, session)


class GameItem:
    """Represents item inside inventory."""

    def __init__(self, item: Item[AnyAttachment], tier: Rarity, id: int) -> None:
        self.item = item
        self._power = 0
        self.tier = tier
        self.id = id

        rarity = item.rarity

        if isinstance(rarity, Rarity):
            self.rarity = self.max_rarity = rarity

        else:
            self.rarity, self.max_rarity = rarity


    def can_transform(self) -> bool:
        """Returns True if item has enough power to transform and has't reached max transform tier, False otherwise"""
        if 1 + 1 == 2:  # TODO: condition(s) for power
            return False

        if self.tier < self.max_rarity:
            return True

        return False


    def transform(self) -> None:
        """Transforms the item to higher tier, if it has enough power"""
        if not self.can_transform():
            raise ValueError('Not enough power to transform')

        self.tier = Rarity.next_tier(self.tier)
        clear_cache(self, 'add_power')
        self._power = 0


    @property
    def power(self) -> int:
        return self._power


    def add_power(self, power: int) -> None:
        if not isinstance(power, int):
            raise TypeError('Invalid type')

        if power < 0:
            raise ValueError('Negative value')

        self._power += power


    @cached_property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""
        upper = self.max_rarity
        lower = self.rarity
        current = self.tier
        item = self.item

        return 0


class GameVars(NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: dict[str, int] = {'health': 15}

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT


DEFAULT_VARS = GameVars()


def format_count(it: Iterable[Any]) -> Iterator[str]:
    return (f'{item}{f" x{count}" * (count > 1)}' for item, count in Counter(filter(None, it)).items())


def clear_cache(obj: object, name: str) -> None:
    """For use with @cachedproperty attributes."""
    if name in obj.__dict__:
        obj.__delattr__(name)


class _Items(TypedDict):
    torso: Item[Attachments] | None
    legs:  Item[Attachment] | None
    drone: Item[Attachment] | None
    side1: Item[Attachment] | None
    side2: Item[Attachment] | None
    side3: Item[Attachment] | None
    side4: Item[Attachment] | None
    top1:  Item[Attachment] | None
    top2:  Item[Attachment] | None
    teleporter:     Item[None] | None
    charge_engine:  Item[None] | None
    grappling_hook: Item[None] | None
    mod1: Item[None] | None
    mod2: Item[None] | None
    mod3: Item[None] | None
    mod4: Item[None] | None
    mod5: Item[None] | None
    mod6: Item[None] | None
    mod7: Item[None] | None
    mod8: Item[None] | None


class Mech:
    """Represents a mech build."""
    if TYPE_CHECKING:
        torso: Item[Attachments] | None
        legs:  Item[Attachment] | None
        drone: Item[Attachment] | None
        side1: Item[Attachment] | None
        side2: Item[Attachment] | None
        side3: Item[Attachment] | None
        side4: Item[Attachment] | None
        top1:  Item[Attachment] | None
        top2:  Item[Attachment] | None
        teleporter:     Item[None] | None
        charge_engine:  Item[None] | None
        grappling_hook: Item[None] | None
        mod1: Item[None] | None
        mod2: Item[None] | None
        mod3: Item[None] | None
        mod4: Item[None] | None
        mod5: Item[None] | None
        mod6: Item[None] | None
        mod7: Item[None] | None
        mod8: Item[None] | None

    def __init__(self, *, vars: GameVars=DEFAULT_VARS):
        self._items: _Items = dict.fromkeys(_Items.__annotations__, None)  # type: ignore
        self.items_to_load: set[Item[AnyAttachment]] = set()
        self.game_vars = vars


    def __getattr__(self, name: Any) -> Item[AnyAttachment] | None:
        try:
            return self._items[name]

        except KeyError:
            raise AttributeError(f'{type(self).__name__} object has no attribute "{name}"') from None


    def __setitem__(self, place: str | tuple[AnyType, int], item: Item[AnyAttachment] | None) -> None:
        if not isinstance(item, (Item, type(None))):
            raise TypeError(f'Expected Item object or None, got {type(item)}')

        pos = None

        if isinstance(place, tuple):
            place, pos = place

        clear_cache(self, 'calc_stats')

        if item is not None and item.displayable:
            clear_cache(self, 'image')

            if item._image is None:
                self.items_to_load.add(item)

        item_type = place.lower()

        if item_type in self._items:
            self._items[item_type] = item
            return

        if pos is None:
            raise TypeError(f'"{item_type}" requires pos passed')

        if item_type == 'module':
            if not 0 < pos <= 8:
                raise ValueError(f'Pos outside range 1-8')

            self._items[f'mod{pos}'] = item

        elif item_type == 'side_weapon':
            if not 0 < pos <= 4:
                raise ValueError(f'Pos outside range 1-4')

            self._items[f'side{pos}'] = item

        elif item_type == 'top_weapon':
            if not 0 < pos <= 2:
                raise ValueError(f'Pos outside range 1-2')

            self._items[f'top{pos}'] = item

        else:
            raise TypeError('Invalid item type passed')


    def __str__(self) -> str:
        string_parts = [f'{item.type.capitalize()}: {item}' for item in (self.torso, self.legs, self.drone) if item is not None]

        if weapon_string := ', '.join(format_count(self.iter_weapons())):
            string_parts.append('Weapons: ' + weapon_string)

        string_parts.extend(f'{item.type.capitalize()}: {item}' for item in self.iter_specials() if item is not None)

        if modules := ', '.join(format_count(self.iter_modules())):
            string_parts.append('Modules: ' + modules)

        return '\n'.join(string_parts)


    @property
    def weight(self) -> int:
        return self.calc_stats.get('weight', 0)


    @property
    def is_valid(self) -> bool:
        return (self.torso is not None
                and self.legs is not None
                and any(wep is not None for wep in self.iter_weapons())
                and self.weight <= self.game_vars.MAX_OVERWEIGHT)


    @cached_property
    def calc_stats(self) -> AnyStats:
        stats_cache = AnyStats()

        for item in self.iter_items():
            if item is None:
                continue

            for key in WORKSHOP_STATS.keys():
                if key in item.stats:
                    if key not in stats_cache:
                        stats_cache[key] = 0

                    stats_cache[key] += item.stats[key]

        if (weight := stats_cache.setdefault('weight', 0)) > self.game_vars.MAX_WEIGHT:
            for stat, pen in self.game_vars.PENALTIES.items():
                stats_cache[stat] = stats_cache.get(stat, 0) - (weight - self.game_vars.MAX_WEIGHT) * pen

        return stats_cache


    @property
    def sorted_stats(self) -> Iterator[tuple[str, int]]:
        stats = self.calc_stats
        reference = tuple(WORKSHOP_STATS.keys())

        for stat in sorted(stats, key=reference.index):
            yield stat, stats[stat]


    def buffed_stats(self, buffs: ArenaBuffs) -> Iterator[tuple[str, int]]:
        for stat, value in self.sorted_stats:
            yield stat, buffs.total_buff(stat, value)


    def print_stats(self, buffs: ArenaBuffs=None) -> str:
        main_str = ''

        if buffs is None:
            bank = self.sorted_stats

        else:
            bank = self.buffed_stats(buffs)

        for stat, value in bank:
            name, icon = STAT_NAMES[stat]
            if stat == 'weight':
                emojis = '👽⚙️✅👌❗⛔'

                e = emojis[
                      (value >= 0)
                    + (value >  self.game_vars.MAX_WEIGHT - 10)
                    + (value >= self.game_vars.MAX_WEIGHT)
                    + (value >  self.game_vars.MAX_WEIGHT)
                    + (value >  self.game_vars.MAX_OVERWEIGHT)]

                main_str += f'{icon} **{value}** {e} {name}\n'

            else:
                main_str += f'{icon} **{value}** {name}\n'

        return main_str


    @cached_property
    def image(self) -> Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `RuntimeError`"""
        if self.torso is None:
            raise RuntimeError('Cannot create image without torso set')

        canvas = MechRenderer(self.torso)

        if self.legs is not None:
            canvas.add_image(self.legs, 'legs')

        for item, layer in zip(self.iter_weapons(), ('side1', 'side2', 'side3', 'side4', 'top1', 'top2')):
            if item is None:
                continue

            canvas.add_image(item, layer)

        if self.drone is not None:
            width, height = get_image_w_h(self.drone.image)
            t_width, t_height = get_image_w_h(self.torso.image)
            self.drone.attachment = Attachment(x=t_width - width - 50, y=height + 25)

            canvas.add_image(self.drone, 'drone')

        return canvas.finalize()


    @property
    def has_image_cached(self) -> bool:
        """Returns True if the image is in cache, False otherwise.
        Does not check if the cache has been changed."""
        return 'image' in self.__dict__


    async def load_images(self, session: aiohttp.ClientSession) -> None:
        """Bulk loads item images"""
        coros = {item.load_image(session) for item in self.iter_items() if item is not None if item._image is None}

        if coros:
            await asyncio.wait(coros, timeout=5, return_when='ALL_COMPLETED')


    def iter_weapons(self) -> Iterator[Item[Attachment] | None]:
        """Iterator over mech's side and top weapons"""
        items = self._items
        yield items['side1']
        yield items['side2']
        yield items['side3']
        yield items['side4']
        yield items['top1']
        yield items['top2']

    def iter_modules(self) -> Iterator[Item[None] | None]:
        """Iterator over mech's modules"""
        items = self._items
        yield items['mod1']
        yield items['mod2']
        yield items['mod3']
        yield items['mod4']
        yield items['mod5']
        yield items['mod6']
        yield items['mod7']
        yield items['mod8']

    def iter_specials(self) -> Iterator[Item[None] | None]:
        """Iterator over mech's specials, in order: tele, charge, hook"""
        items = self._items
        yield items['teleporter']
        yield items['charge_engine']
        yield items['grappling_hook']

    def iter_items(self) -> Iterator[Item[AnyAttachment] | None]:
        """Iterator over all mech's items"""
        yield from self._items.values()  # type: ignore


class ArenaBuffs:
    ref_def = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    ref_hp  = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    stat_ref = ('eneCap', 'eneReg', 'eneDmg', 'heaCap', 'heaCol', 'heaDmg', 'phyDmg',
                'expDmg', 'eleDmg', 'phyRes', 'expRes', 'eleRes', 'health', 'backfire')

    def __init__(self) -> None:
        self.levels = dict.fromkeys(self.stat_ref, 0)


    def __getitem__(self, key: str) -> int:
        return self.levels[key]


    def total_buff(self, stat: str, value: int) -> int:
        """Buffs a value according to given stat."""
        if stat not in self.levels:
            return value

        level = self.levels[stat]

        if stat == 'health':
            return value + self.ref_hp[level]

        return round(value * (1 + self.get_percent(stat, level) / 100))


    def total_buff_difference(self, stat: str, value: int) -> tuple[int, int]:
        """Buffs a value and returns the total as well as the difference between the total and initial value."""
        buffed = self.total_buff(stat, value)
        return buffed, buffed - value


    @classmethod
    def get_percent(cls, stat: str, level: int) -> int:
        if stat == 'health':
            raise TypeError('"Health" stat has absolute increase, not percent')

        value = cls.ref_def[level]

        if stat == 'backfire':
            return -value

        if stat.endswith('Res'):
            return value * 2

        return value


    @classmethod
    def buff_as_str(cls, stat: str, level: int) -> str:
        if stat == 'health':
            return f'+{cls.ref_hp[level]}'

        return f'{cls.get_percent(stat, level):+}%'


    def buff_as_str_aware(self, stat: str) -> str:
        return self.buff_as_str(stat, self.levels[stat])


    @classmethod
    def iter_as_str(cls, stat: str) -> Iterator[str]:
        levels = len(cls.ref_hp) if stat == 'health' else len(cls.ref_def)

        for n in range(levels):
            yield cls.buff_as_str(stat, n)


    @classmethod
    def maxed(cls) -> ArenaBuffs:
        self = cls.__new__(cls)

        self.levels = dict.fromkeys(cls.stat_ref, len(cls.ref_def)-1)
        self.levels['health'] = len(cls.ref_hp) - 1

        return self


@dataclass
class Player:
    id: int
    builds: dict[str, Mech] = field(hash=False, default_factory=dict)
    arena_buffs: ArenaBuffs = field(hash=False, default_factory=ArenaBuffs, init=False)
    active_build: str       = field(hash=False, default='', init=False)


    def get_or_create_build(self, possible_name: str=None) -> Mech:
        """Retrieves active build if player has one, otherwise creates a new one.

        Parameters
        -----------
        possible_name: :class:`str | None`
            The name to create a new build with. Ignored if player has active build.
            If not passed, the name will be randomized.
        """
        if self.active_build == '':
            return self.new_build(possible_name)

        return self.builds[self.active_build]


    def get_active_build(self) -> Mech | None:
        """Returns active build if player has one, `None` otherwise."""
        return self.builds.get(self.active_build)


    def new_build(self, name: str=None) -> Mech:
        """Creates a new build, sets it as active and returns it.

        Parameters
        -----------
        name: `str | None`
            The name to assign to the build. If `None`, name will be randomized.
        """
        build = Mech()

        if name is None:
            while (name := random_str(6)) in self.builds:
                pass

        self.builds[name] = build
        self.active_build = name
        return build


    def rename(self, old_name: str, new_name: str) -> None:
        """Changes the name a build is assigned to.

        Parameters
        -----------
        old_name: `str`
            Name of existing build to be changed.
        new_name: `str`
            New name for the build.

        Raises
        -------
        ValueError
            Old name not found or new name already in use.
        """
        if old_name not in self.builds:
            raise ValueError('Build not found')

        if new_name in self.builds:
            raise ValueError('Provided name already present')

        self.builds[new_name] = self.builds.pop(old_name)


    def delete(self, name: str) -> None:
        """Deletes build from player's builds.

        Parameters
        -----------
        name: `str`
            The name of the build to delete.

        Raises
        -------
        ValueError
            Name not found."""
        if name not in self.builds:
            raise ValueError('Build not found')

        del self.builds[name]
