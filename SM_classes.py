from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from typing import *

import aiohttp
from PIL import Image

from enums import STAT_NAMES, WORKSHOP_STATS, Elements, Icons, Rarity
from functions import js_format
from image_manipulation import MechRenderer, get_image, get_image_w_h

if TYPE_CHECKING:
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
    width: NotRequired[int]
    height: NotRequired[int]
    type: AnyType
    element: AnyElement
    transform_range: str
    stats:  AnyStats
    divine: AnyStats
    tags: NotRequired[list[str]]
    attachment: NotRequired[Attachment | Attachments]


# AttachmentType = TypeVar('AttachmentType', Attachment, Attachments, None)
AttachmentType = TypeVar('AttachmentType', bound=AnyAttachment)

@dataclass
class ItemData(Generic[AttachmentType]):
    """Represents data about an in-game item."""
    id: int
    name: str
    pack: PackConfig
    image: InitVar[str]
    _type:  InitVar[str]
    stats: AnyStats = field(repr=False, hash=False)
    transform_range: InitVar[str]
    element: Elements = Elements.OMNI
    attachment: AttachmentType = cast(AttachmentType, None)
    divine: AnyStats | None = field(default=None, repr=False, hash=False)


    def __post_init__(self, image: str, type: str, transform_range: str) -> None:
        self.image_url = js_format(image, url=self.pack['base_url'])
        self.icon = Icons[type]

        val_a, _, val_b = transform_range.partition('-')
        self.rarity = (Rarity[val_a], Rarity[val_b]) if val_b else Rarity[val_a]

        self._image: Image.Image | None = None


    @property
    def type(self) -> str:
        return self.icon.name


# item = ItemData(1, 'foo', {'key': '', 'name': '', 'base_url': '', 'description': ''}, 'foo', 'TORSO', AnyStats(), '', element=Elements.HEAT, attachment=None)


class Item(Generic[AttachmentType]):
    """Represents a single item."""
    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        type: str,
        stats: AnyStats,
        transform_range: str,
        pack: PackConfig,
        divine: AnyStats = None,
        element: str = 'OMNI',
        attachment: AttachmentType = None,
        **kwargs: Any
    ) -> None:

        self.id = id
        self.name = str(name)

        self.image_url = js_format(str(image), url=pack['base_url'])
        self.pack = pack
        self._image: Image.Image | None = None

        self.icon = Icons[type]  # this will also validate if type is of correct type
        self.stats = stats
        self.divine = divine

        val_a, _, val_b = transform_range.partition('-')
        self.rarity = (Rarity[val_a], Rarity[val_b]) if val_b else Rarity[val_a]
        self.element = Elements[element]

        self.attachment = attachment
        self.kwargs = kwargs


    # @classmethod
    # def from_dict(cls, item_dict: ItemDict, pack: PackConfig) -> Item[AnyAttachment]:
    #     return Item(pack=pack, **item_dict)


    def __str__(self) -> str:
        return self.name


    def __repr__(self) -> str:
        return '<{0.name} - {0.element} {0.type} {0.rarity} {0.stats}>'.format(self)


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
        return hash((self.id, self.name, self.type))


    @property
    def type(self) -> str:
        return self.icon.name


    # @property
    # def attachment(self) -> AttachmentType:
    #     return self._attachment  # type: ignore


    # @attachment.setter
    # def attachment(self, attach: AttachmentType) -> None:
    #     self._attachment = attach


    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.type not in {'TELEPORTER', 'CHARGE', 'HOOK', 'MODULE'}


    @property
    def image(self) -> Image.Image:
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

    def __init__(self, reference: Item, tier: Rarity, id: int) -> None:
        self.ref = reference
        self._power = 0
        self.tier = tier
        self.id = id

        rarity = reference.rarity

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
        del self.max_power
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
        item = self.ref

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



class _Items(TypedDict):
    torso:  Item[Attachments] | None
    legs:   Item[Attachment] | None
    drone:  Item[Attachment] | None
    side1:  Item[Attachment] | None
    side2:  Item[Attachment] | None
    side3:  Item[Attachment] | None
    side4:  Item[Attachment] | None
    top1:   Item[Attachment] | None
    top2:   Item[Attachment] | None
    tele:   Item[None] | None
    charge: Item[None] | None
    hook:   Item[None] | None
    mod1:   Item[None] | None
    mod2:   Item[None] | None
    mod3:   Item[None] | None
    mod4:   Item[None] | None
    mod5:   Item[None] | None
    mod6:   Item[None] | None
    mod7:   Item[None] | None
    mod8:   Item[None] | None


class Mech:
    """Represents a mech build."""
    if TYPE_CHECKING:
        torso:  Item[Attachments] | None
        legs:   Item[Attachment] | None
        drone:  Item[Attachment] | None
        side1:  Item[Attachment] | None
        side2:  Item[Attachment] | None
        side3:  Item[Attachment] | None
        side4:  Item[Attachment] | None
        top1:   Item[Attachment] | None
        top2:   Item[Attachment] | None
        tele:   Item[None] | None
        charge: Item[None] | None
        hook:   Item[None] | None
        mod1:   Item[None] | None
        mod2:   Item[None] | None
        mod3:   Item[None] | None
        mod4:   Item[None] | None
        mod5:   Item[None] | None
        mod6:   Item[None] | None
        mod7:   Item[None] | None
        mod8:   Item[None] | None

    def __init__(self, *, vars: GameVars=DEFAULT_VARS):
        self._items: _Items = dict.fromkeys(_Items.__annotations__, None)  # type: ignore
        self.items_to_load: set[Item] = set()
        self.game_vars = vars


    def __getattr__(self, name: Any) -> Item[AnyAttachment] | None:
        try:
            return self._items[name]

        except KeyError:
            raise AttributeError(f'{type(self).__name__} object has no attribute "{name}"') from None


    def __setitem__(self, place: str | tuple[AnyType, int], item: Item[AnyAttachment] | None) -> None:
        if not isinstance(item, (Item, type(None))):
            raise TypeError

        pos = None

        if isinstance(place, tuple):
            place, pos = place

        if 'calc_stats' in self.__dict__:
            del self.calc_stats  # force to calculate again

        if item is not None and item.displayable:
            if 'image' in self.__dict__:
                del self.image

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

        string_parts.extend(f'{item.type.capitalize()}: {item}' for item in (self.tele, self.charge, self.hook) if item is not None)

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


    @property
    def display_stats(self) -> str:
        main_str = ''

        for stat, value in self.sorted_stats:
            name, icon = STAT_NAMES[stat]
            if stat == 'weight':
                emojis = '👽⚙️👌❗⛔'

                e = emojis[
                    (value >= 0)
                    + (value >= self.game_vars.MAX_WEIGHT)
                    + (value > self.game_vars.MAX_WEIGHT)
                    + (value > self.game_vars.MAX_OVERWEIGHT)]

                main_str += f'{icon} **{value}** {e} {name}\n'

            else:
                main_str += f'{icon} **{value}** {name}\n'

        return main_str


    @property
    def buff_stats(self) -> str:
        main_str = ''

        for stat, value in self.sorted_stats:
            name, icon = STAT_NAMES[stat]
            if stat == 'weight':
                emojis = '👽⚙️👌❗⛔'

                e = emojis[
                    (value >= 0)
                    + (value >= self.game_vars.MAX_WEIGHT)
                    + (value > self.game_vars.MAX_WEIGHT)
                    + (value > self.game_vars.MAX_OVERWEIGHT)]

                main_str += f'{icon} **{value}** {e} {name}\n'

            else:
                main_str += f'{icon} **{value}** {name}\n'

        return main_str



    @cached_property
    def image(self) -> Image.Image:
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
    def image_changed(self) -> bool:
        """Returns True if the image has modified, False otherwise"""


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

    def iter_items(self) -> Iterator[Item[AnyAttachment] | None]:
        """Iterator over all mech's items"""
        yield from self._items.values()  # type: ignore


class ArenaBuffs:
    ref_def = (0, 1, 3,  5,  7,  9, 11, 13, 15, 17, 20)
    ref_hp  = (0, None, None, None, 90, 120, None, None, None, None, 300, 350)
    #                                        150   180   210   240 ?
    stat_ref = ('eneCap', 'eneReg', 'eneDeg', 'heaCap', 'heaCol', 'heaDmg', 'phyDmg',
                'expDmg', 'eleDmg', 'phyRes', 'expRes', 'eleRes', 'health', 'backfire')

    def __init__(self) -> None:
        self.level_ref = dict.fromkeys(self.stat_ref, 0)


    @staticmethod
    def safe_get(level: int, bank: tuple[int | None, ...]) -> int:
        while level > 0:
            value = bank[level]

            if value is not None:
                return value

            level -= 1

        return 0


    def get_buff(self, stat: str, value: int) -> int:
        if stat not in self.level_ref:
            return value

        level = self.level_ref[stat]

        if stat == 'health':
            return value + self.safe_get(level, self.ref_hp) # +350

        if stat == 'backfire':
            return round(value * (1 - self.safe_get(level, self.ref_def) / 100)) # -20%

        if stat in {'phyRes', 'expRes', 'eleRes'}:
            return round(value * (1 + self.safe_get(level, self.ref_def) / 50))  # +40%

        return round(value * (1 + self.safe_get(level, self.ref_def) / 100))  # +20%


    @classmethod
    def maxed(cls) -> ArenaBuffs:
        self = cls.__new__(cls)

        self.level_ref = dict.fromkeys(cls.stat_ref, len(cls.ref_def)-1)
        self.level_ref['health'] = len(cls.ref_hp) - 1

        return self
