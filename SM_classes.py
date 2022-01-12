from __future__ import annotations

import asyncio
import uuid
from typing import (TYPE_CHECKING, Any, Callable, Dict, Generic, Iterator,
                    Literal, NamedTuple, TypedDict, TypeVar, cast)

import bson
from odmantic import Field, Model
from pydantic import NonNegativeInt, PrivateAttr, ValidationError, validator
from pydantic.fields import ModelField

from enums import (STAT_NAMES, WORKSHOP_STATS, Elements, Icons, Rarity,
                   RarityRange)
from images import MechRenderer, get_image, get_image_size
from utils import MISSING, format_count, js_format, random_str

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image
    from typing_extensions import NotRequired

    class PackConfig(TypedDict):
        key: str
        name: str
        base_url: str
        description: str


AnyType = Literal['TORSO', 'LEGS', 'DRONE', 'SIDE_WEAPON', 'TOP_WEAPON', 'TELE', 'CHARGE', 'HOOK', 'MODULE']
AnyElement = Literal['PHYSICAL', 'EXPLOSIVE', 'ELECTRIC', 'COMBINED']


class AnyStats(TypedDict, total=False):
    # stats sorted in order they appear in-game
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
    phyDmg: list[int]
    phyResDmg: int
    eleDmg: list[int]
    eneDmg: int
    eneCapDmg: int
    eneRegDmg: int
    eleResDmg: int
    expDmg: list[int]
    heaDmg: int
    heaCapDmg: int
    heaColDmg: int
    expResDmg: int
    walk: int
    jump: int
    range: list[int]
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


Attachments = Dict[str, Attachment]
AttachmentType = TypeVar('AttachmentType', Attachment, Attachments, None)


class ItemDictBase(TypedDict):
    id: int
    name: str
    image: str
    width:  NotRequired[int]
    height: NotRequired[int]
    type: AnyType
    element: AnyElement
    transform_range: str
    stats:  AnyStats
    divine: NotRequired[AnyStats]
    tags: NotRequired[list[str]]


class ItemDictAttachment(ItemDictBase):
    attachment: Attachment


class ItemDictAttachments(ItemDictBase):
    attachment: Attachments


ItemDict = ItemDictBase | ItemDictAttachment | ItemDictAttachments


class ItemPack(TypedDict):
    config: PackConfig
    items: list[ItemDict]


class Item(Generic[AttachmentType]):
    """Represents a single item."""
    loader: Callable[[str], AnyItem]

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
        **extra: Any
    ) -> None:

        self.id = id
        self.name = str(name)

        self.image_url = js_format(image, url=pack['base_url'])
        self.pack = pack
        self._image: Image | None = None

        self.icon = Icons[type.upper()]  # this will also validate if type is of correct type
        self.stats = stats
        self.divine = divine

        self.rarity = RarityRange.from_string(transform_range)
        self.element = Elements[element]

        self.attachment = attachment
        self.extra = extra

    def __str__(self) -> str:
        return self.name

    def __index__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return '<Item {0.name!r}: element={0.element.name} type={0.type} rarity={0.rarity!r} stats={0.stats}>'.format(self)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Item):
            return False

        return (o.id == self.id
                and o.image_url == self.image_url
                and o.name == self.name
                and o.type == self.type
                and o.stats == self.stats
                and o.divine == self.divine
                and o.rarity == self.rarity)

    def __hash__(self) -> int:
        return hash((self.id, self.name, self.type, self.rarity, self.element, self.pack['key']))

    @property
    def type(self) -> str:
        return self.icon.name

    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.type not in {'TELE', 'CHARGE', 'HOOK', 'MODULE'}

    @property
    def image(self) -> Image:
        """Returns a copy of image for this item. Before this property is ever retrieved, load_image needs to be called."""
        if self._image is None:
            raise RuntimeError('load_image was never called')

        if 'width' in self.extra or 'height' in self.extra:
            new_width = self.extra.get('width',  0)
            new_height = self.extra.get('height', 0)

            width, height = get_image_size(self._image)
            width = new_width or width
            height = new_height or height

            return self._image.resize((width, height))

        return self._image.copy()

    @property
    def has_image(self) -> bool:
        """Whether item has image cached."""
        return self._image is not None

    async def load_image(self, session: ClientSession, /, *, force: bool = False) -> None:
        """Loads the image from web

        Parameters
        -----------
        session:
            the session to perform the image request with.
        force:
            if true and item has an image cached, it will be overwritten."""
        if self.has_image and not force:
            return

        if self.image_url is None:
            raise ValueError('Image URL was not set')

        self._image = await get_image(self.image_url, session)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Item | bytes, field: ModelField) -> Item:
        match v:
            case bytes():
                return cls.loader(v.decode())

            case Item():
                if not field.sub_fields:
                    return v

                attachment = field.sub_fields[0]
                _, error = attachment.validate(v.attachment, {}, loc='item')

                if error:
                    raise ValidationError([error], InvItem)

                return v

            case _:
                raise TypeError('Invalid type passed')

    @classmethod
    def __bson__(cls, v: AnyItem) -> bytes:
        return v.name.encode()


AnyItem = Item[Attachment] | Item[Attachments] | Item[None]


class InvItem(Model, Generic[AttachmentType]):
    """Represents item inside inventory."""

    underlying: Item[AttachmentType]
    tier: Rarity
    power: NonNegativeInt = 0
    UUID: uuid.UUID = Field(default_factory=uuid.uuid4, primary_field=True)

    @validator('tier')
    def tier_in_bounds(cls, v: Rarity, values: dict[str, Item[AttachmentType]]) -> Rarity:
        item = values['underlying']

        if v in item.rarity:
            return v

        raise ValueError(f'{v.name} is outside item rarity bounds')

    def __repr__(self) -> str:
        return f'<InvItem item={self.underlying!r} tier={self.max_rarity} power={self.power} UUID={self.UUID}>'

    @property
    def type(self) -> str:
        """Type of the underlying item."""
        return self.underlying.type

    @property
    def element(self) -> Elements:
        return self.underlying.element

    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.underlying.displayable

    @property
    def image(self) -> Image:
        """Returns a copy of image for this item. Before this property is ever retrieved, load_image needs to be called."""
        return self.underlying.image

    @property
    def has_image(self) -> bool:
        """Whether item has image cached."""
        return self.underlying.has_image

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
        self.power = 0

    @property
    def min_rarity(self) -> Rarity:
        return self.underlying.rarity.min

    @property
    def max_rarity(self) -> Rarity:
        return self.underlying.rarity.max

    @property
    def max_power(self) -> int:
        """Returns the total power necessary to max the item at current tier"""
        upper = self.max_rarity
        lower = self.min_rarity
        current = self.tier
        item = self.underlying

        return 0

    @classmethod
    def from_item(cls, item: Item[AttachmentType]) -> InvItem[AttachmentType]:
        return cls(underlying=item, tier=item.rarity.max)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls: type[InvItem[AttachmentType]], v: InvItem | bytes, field: ModelField) -> InvItem[AttachmentType]:
        print('yeah', field)
        match v:
            case bytes():
                data = cast(dict[str, Any], bson.decode(v))
                print('data', data)
                return InvItem(**data)

            case InvItem():
                if not field.sub_fields:
                    return v

                attachment = field.sub_fields[0]
                _, error = attachment.validate(v.underlying.attachment, {}, loc='item')

                if error:
                    raise ValidationError([error], cls)

                return v

            case _:
                raise TypeError('Invalid type passed')

    @classmethod
    def __bson__(cls, v: AnyInvItem) -> bytes:
        return bson.encode(dict(underlying=v.underlying, tier=v.tier, power=v.power, UUID=v.UUID))


AnyInvItem = InvItem[Attachment] | InvItem[Attachments] | InvItem[None]


class GameVars(NamedTuple):
    MAX_WEIGHT: int = 1000
    OVERWEIGHT: int = 10
    PENALTIES: dict[str, int] = {'health': 15}

    @property
    def MAX_OVERWEIGHT(self) -> int:
        return self.MAX_WEIGHT + self.OVERWEIGHT


DEFAULT_VARS = GameVars()


class _InvItems(TypedDict):
    torso:  InvItem[Attachments] | None
    legs:   InvItem[Attachment] | None
    drone:  InvItem[Attachment] | None
    side1:  InvItem[Attachment] | None
    side2:  InvItem[Attachment] | None
    side3:  InvItem[Attachment] | None
    side4:  InvItem[Attachment] | None
    top1:   InvItem[Attachment] | None
    top2:   InvItem[Attachment] | None
    tele:   InvItem[None] | None
    charge: InvItem[None] | None
    hook:   InvItem[None] | None
    mod1:   InvItem[None] | None
    mod2:   InvItem[None] | None
    mod3:   InvItem[None] | None
    mod4:   InvItem[None] | None
    mod5:   InvItem[None] | None
    mod6:   InvItem[None] | None
    mod7:   InvItem[None] | None
    mod8:   InvItem[None] | None


class Mech(Model):
    """Represents a mech build."""

    game_vars: GameVars = DEFAULT_VARS
    __items__: _InvItems = PrivateAttr(default_factory=lambda: dict.fromkeys(_InvItems.__annotations__, None))
    __stats__: AnyStats = PrivateAttr(default_factory=dict)
    __image__: Image = PrivateAttr(MISSING)

    if TYPE_CHECKING:
        torso:  InvItem[Attachments] | None
        legs:   InvItem[Attachment] | None
        drone:  InvItem[Attachment] | None
        side1:  InvItem[Attachment] | None
        side2:  InvItem[Attachment] | None
        side3:  InvItem[Attachment] | None
        side4:  InvItem[Attachment] | None
        top1:   InvItem[Attachment] | None
        top2:   InvItem[Attachment] | None
        tele:   InvItem[None] | None
        charge: InvItem[None] | None
        hook:   InvItem[None] | None
        mod1:   InvItem[None] | None
        mod2:   InvItem[None] | None
        mod3:   InvItem[None] | None
        mod4:   InvItem[None] | None
        mod5:   InvItem[None] | None
        mod6:   InvItem[None] | None
        mod7:   InvItem[None] | None
        mod8:   InvItem[None] | None

    def __getattr__(self, name: Any):
        try:
            return self.__items__[name]

        except KeyError:
            raise AttributeError(f'{type(self).__name__} object has no attribute "{name}"') from None

    def __setitem__(self, place: str | tuple[str, int], item: AnyInvItem | None) -> None:
        if not isinstance(item, (InvItem, type(None))):
            raise TypeError(f'Expected Item object or None, got {type(item)}')

        pos = None

        if isinstance(place, tuple):
            place, pos = place

        del self.stats

        item_type = place.lower()

        if item_type in self.__items__:
            self.invalidate_image(item, self.__items__[item_type])
            self.__items__[item_type] = item
            return

        if pos is None:
            raise TypeError(f'"{item_type}" requires pos passed')

        item_types: dict[str, tuple[str, int]] = {
            "module": ("mod", 8),
            "side_weapon": ("side", 4),
            "top_weapon": ("top", 2)}

        if item_type not in item_types:
            raise TypeError('Invalid item type passed')

        slug, limit = item_types[item_type]

        if not 0 < pos <= limit:
            raise ValueError(f"Position outside range 1-{limit}")

        item_type = slug + str(pos)
        self.invalidate_image(item, self.__items__[item_type])
        self.__items__[item_type] = item

    def __str__(self) -> str:
        string_parts = [f'{item.type.capitalize()}: {item}' for item in (self.torso, self.legs, self.drone) if item is not None]

        if weapon_string := ', '.join(format_count(self.iter_weapons())):
            string_parts.append('Weapons: ' + weapon_string)

        string_parts.extend(f'{item.type.capitalize()}: {item}' for item in self.iter_specials() if item is not None)

        if modules := ', '.join(format_count(self.iter_modules())):
            string_parts.append('Modules: ' + modules)

        return '\n'.join(string_parts)

    # def __repr__(self) -> str:
    #     return '<Mech ' + ', '.join(f'{slot}={item}' for slot, item in self._items.items()) + '>'

    @property
    def weight(self) -> int:
        return self.stats.get('weight', 0)

    @property
    def is_valid(self) -> bool:
        return (self.torso is not None
                and self.legs is not None
                and any(wep is not None for wep in self.iter_weapons())
                and self.weight <= self.game_vars.MAX_OVERWEIGHT)

    @property
    def stats(self) -> AnyStats:
        if self.__stats__:
            return self.__stats__

        stats_cache = self.__stats__

        for item in self.iter_items():
            if item is None:
                continue

            for key in WORKSHOP_STATS.keys():
                if key in item.underlying.stats:
                    if key not in stats_cache:
                        stats_cache[key] = 0

                    stats_cache[key] += item.underlying.stats[key]

        if (weight := stats_cache.setdefault('weight', 0)) > self.game_vars.MAX_WEIGHT:
            for stat, pen in self.game_vars.PENALTIES.items():
                stats_cache[stat] = stats_cache.get(stat, 0) - (weight - self.game_vars.MAX_WEIGHT) * pen

        self.__stats__ = stats_cache
        return stats_cache

    @stats.deleter
    def stats(self) -> None:
        cast(dict, self.__stats__).clear()

    @property
    def sorted_stats(self) -> Iterator[tuple[str, int]]:
        stats = self.stats
        reference = tuple(WORKSHOP_STATS.keys())

        for stat in sorted(stats, key=reference.index):
            yield stat, stats[stat]

    def buffed_stats(self, buffs: ArenaBuffs) -> Iterator[tuple[str, int]]:
        for stat, value in self.sorted_stats:
            yield stat, buffs.total_buff(stat, value)

    def print_stats(self, buffs: ArenaBuffs = None) -> str:
        if buffs is None:
            bank = self.sorted_stats

        else:
            bank = self.buffed_stats(buffs)

        weight, value = next(bank)
        name, icon = STAT_NAMES[weight]

        emojis = ('🗿', '⚙️', '🆗', '👌', '❕', '⛔')
        vars = self.game_vars

        cond = (
            (value >= 0)
            + (value >= vars.MAX_WEIGHT - 10)
            + (value >= vars.MAX_WEIGHT)
            + (value > vars.MAX_WEIGHT)
            + (value > vars.MAX_OVERWEIGHT))

        emoji = emojis[cond]

        main_str = f'{icon} **{value}** {name} {emoji}\n' + \
            '\n'.join('{1} **{2}** {0}'.format(*STAT_NAMES[stat], value) for stat, value in bank)

        return main_str

    @property
    def image(self) -> Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `RuntimeError`"""
        if self.__image__ is not MISSING:
            return self.__image__

        if self.torso is None:
            raise RuntimeError('Cannot create image without torso set')

        canvas = MechRenderer(self.torso.underlying)

        if self.legs is not None:
            canvas.add_image(self.legs.underlying, 'legs')

        for item, layer in zip(self.iter_weapons(), ('side1', 'side2', 'side3', 'side4', 'top1', 'top2')):
            if item is None:
                continue

            canvas.add_image(item.underlying, layer)

        # drone is offset-relative so we need to handle that here
        if self.drone is not None:
            width, height = get_image_size(self.drone.image)
            self.drone.underlying.attachment = Attachment(
                x=canvas.pixels_left + width // 2,
                y=canvas.pixels_above + height + 25)

            canvas.add_image(self.drone.underlying, 'drone')

        self.__image__ = canvas.finalize()
        return self.__image__

    @image.deleter
    def image(self) -> None:
        self.__image__ = MISSING

    def invalidate_image(self, new: AnyInvItem | None, old: AnyInvItem | None) -> None:
        if new is not None and new.displayable:
            del self.image
            # self.items_to_load.add(new)

        elif old is not None and old.displayable:
            del self.image

    @property
    def has_image_cached(self) -> bool:
        """Returns True if the image is in cache, False otherwise.
        Does not check if the cache has been changed."""
        return self.__image__ is not MISSING

    async def load_images(self, session: ClientSession) -> None:
        """Bulk loads item images"""
        coros = {item.underlying.load_image(session) for item in self.iter_items() if item is not None if not item.has_image}

        if coros:
            await asyncio.wait(coros, timeout=5, return_when='ALL_COMPLETED')

    def iter_weapons(self) -> Iterator[InvItem[Attachment] | None]:
        """Iterator over mech's side and top weapons"""
        items = self.__items__
        yield items['side1']
        yield items['side2']
        yield items['side3']
        yield items['side4']
        yield items['top1']
        yield items['top2']

    def iter_modules(self) -> Iterator[InvItem[None] | None]:
        """Iterator over mech's modules"""
        items = self.__items__

        for n in range(1, 9):
            yield items[f'mod{n}']

    def iter_specials(self) -> Iterator[InvItem[None] | None]:
        """Iterator over mech's specials, in order: tele, charge, hook"""
        items = self.__items__
        yield items['tele']
        yield items['charge']
        yield items['hook']

    def iter_items(self) -> Iterator[AnyInvItem | None]:
        """Iterator over all mech's items"""
        yield from self.__items__.values()  # type: ignore

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: bytes | Mech) -> Mech:
        match v:
            case bytes():
                items = cast(_InvItems, bson.decode(v))

                if not isinstance(items, dict):
                    raise TypeError('bytes object passed but it did not parse to dict')

                mech = Mech()
                mech.__items__ = items

                return mech

            case Mech():
                return v

            case _:
                raise TypeError('Invalid type passed')

    @classmethod
    def __bson__(cls, inst: Mech) -> bytes:
        return bson.encode(inst.__items__)


class ArenaBuffs:
    ref_def = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 20)
    ref_hp = (0, +10, +30, +60, 90, 120, 150, 180, +220, +260, 300, 350)
    stat_ref = ('eneCap', 'eneReg', 'eneDmg', 'heaCap', 'heaCol', 'heaDmg', 'phyDmg',
                'expDmg', 'eleDmg', 'phyRes', 'expRes', 'eleRes', 'health', 'backfire')

    def __init__(self, levels: dict[str, int] = None) -> None:
        self.levels = levels or dict.fromkeys(self.stat_ref, 0)

    def __getitem__(self, key: str) -> int:
        return self.levels[key]

    def __repr__(self) -> str:
        return '<ArenaBuffs ' + ', '.join(f'{stat}={lvl}' for stat, lvl in self.levels.items()) + '>'

    @property
    def is_at_zero(self) -> bool:
        """Whether all buffs are at level 0"""
        return all(v == 0 for v in self.levels.values())

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
        match stat:
            case 'health':
                raise TypeError('"Health" stat has absolute increase, not percent')

            case 'backfire':
                return -cls.ref_def[level]

            case 'expRes' | 'eleRes' | 'phyRes':
                return cls.ref_def[level] * 2

            case _:
                return cls.ref_def[level]

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

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ArenaBuffs:
        match v:
            case bytes():
                levels = bson.decode(v)

                if not isinstance(levels, dict):
                    raise TypeError('Received bytes object but it did not parse to dict')

                return cls(levels)

            case ArenaBuffs():
                return v

            case _:
                raise TypeError('Invalid type passed')

    @classmethod
    def __bson__(cls, v: ArenaBuffs) -> bytes:
        return bson.encode(v.levels)


class Player(Model):
    """Represents a SuperMechs player."""
    id: int = Field(primary_field=True)
    builds: Dict[str, Mech] = Field(default_factory=dict, allow_mutation=False)
    arena_buffs: ArenaBuffs = Field(default_factory=ArenaBuffs, allow_mutation=False)
    inventory: Dict[uuid.UUID, AnyInvItem] = Field(default_factory=dict, allow_mutation=False)
    active_build_name: str = ''
    level: NonNegativeInt = 0
    exp:   NonNegativeInt = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def get_or_create_build(self, possible_name: str = None, /) -> Mech:
        """Retrieves active build if player has one, otherwise creates a new one.

        Parameters
        -----------
        possible_name:
            The name to create a new build with. Ignored if player has active build.
            If not passed, the name will be randomized.
        """
        if self.active_build_name == '':
            return self.new_build(possible_name)

        return self.builds[self.active_build_name]

    @property
    def active_build(self) -> Mech | None:
        """Returns active build if player has one, `None` otherwise."""
        return self.builds.get(self.active_build_name)

    def new_build(self, name: str = None, /) -> Mech:
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
            raise ValueError('Build not found')

        if new_name in self.builds:
            raise ValueError('Provided name already present')

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
            raise ValueError('Build not found')

        del self.builds[name]
