from __future__ import annotations

import asyncio
from collections import Counter
from enum import Enum
from typing import *

import aiohttp
from PIL import Image

from image_manipulation import bbox_to_w_h, get_image

if TYPE_CHECKING:
    from typing_extensions import NotRequired


class Stat(NamedTuple):
    name: str
    emoji: str


STAT_NAMES = {
    'weight':    Stat('Weight',                   '<:weight:725870760484143174>'),
    'health':    Stat('HP',                       '<:health:725870887588462652>'),
    'eneCap':    Stat('Energy',                   '<:energy:725870941883859054>'),
    'eneReg':    Stat('Regeneration',              '<:regen:725871003665825822>'),
    'heaCap':    Stat('Heat',                       '<:heat:725871043767435336>'),
    'heaCol':    Stat('Cooling',                 '<:cooling:725871075778363422>'),
    'phyRes':    Stat('Physical resistance',      '<:phyres:725871121051811931>'),
    'expRes':    Stat('Explosive resistance',     '<:expres:725871136935772294>'),
    'eleRes':    Stat('Electric resistance',     '<:elecres:725871146716758077>'),
    'phyDmg':    Stat('Damage',                   '<:phydmg:725871208830074929>'),
    'phyResDmg': Stat('Resistance drain',      '<:phyresdmg:725871259635679263>'),
    'expDmg':    Stat('Damage',                   '<:expdmg:725871223338172448>'),
    'heaDmg':    Stat('Heat damage',              '<:headmg:725871613639393290>'),
    'heaCapDmg': Stat('Heat capacity drain',  '<:heatcapdmg:725871478083551272>'),
    'heaColDmg': Stat('Cooling damage',       '<:coolingdmg:725871499281563728>'),
    'expResDmg': Stat('Resistance drain',      '<:expresdmg:725871281311842314>'),
    'eleDmg':    Stat('Damage',                   '<:eledmg:725871233614479443>'),
    'eneDmg':    Stat('Energy drain',             '<:enedmg:725871599517171719>'),
    'eneCapDmg': Stat('Energy capacity drain', '<:enecapdmg:725871420126789642>'),
    'eneRegDmg': Stat('Regeneration damage',    '<:regendmg:725871443815956510>'),
    'eleResDmg': Stat('Resistance drain',      '<:eleresdmg:725871296381976629>'),
    'range':     Stat('Range',                     '<:range:725871752072134736>'),
    'push':      Stat('Knockback',                  '<:push:725871716613488843>'),
    'pull':      Stat('Pull',                       '<:pull:725871734141616219>'),
    'recoil':    Stat('Recoil',                   '<:recoil:725871778282340384>'),
    'retreat':   Stat('Retreat',                 '<:retreat:725871804236955668>'),
    'advance':   Stat('Advance',                 '<:advance:725871818115907715>'),
    'walk':      Stat('Walking',                    '<:walk:725871844581834774>'),
    'jump':      Stat('Jumping',                    '<:jump:725871869793796116>'),
    'uses':      Stat('',                           '<:uses:725871917923303688>'),
    'backfire':  Stat('Backfire',               '<:backfire:725871901062201404>'),
    'heaCost':   Stat('Heat cost',               '<:heatgen:725871674007879740>'),
    'eneCost':   Stat('Energy cost',            '<:eneusage:725871660237979759>')}


AnyType = Literal['TORSO', 'LEGS', 'DRONE', 'SIDE_WEAPON', 'TOP_WEAPON', 'TELEPORTER', 'CHARGE_ENGINE', 'HOOK', 'MODULE']
AnyElement = Literal['PHYSICAL', 'EXPLOSIVE', 'ELECTRIC', 'COMBINED']

# TORSO, LEGS, DRONE, SIDE_WEAPON, TOP_WEAPON, TELEPORTER, CHARGE, HOOK, MODULE

ItemType = TypeVar('ItemType', bound=AnyType)


class AnyStats(TypedDict, total=False):
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


class Attachments(TypedDict):
    leg1: Attachment
    leg2: Attachment
    side1: Attachment
    side2: Attachment
    side3: Attachment
    side4: Attachment
    top1: Attachment
    top2: Attachment



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



class Tier(NamedTuple):
    level: int
    emoji:  str
    color: int

    def __str__(self):
        return self.emoji

class Rarity(Tier, Enum):
    C = Tier(0, '⚪', 0xB1B1B1); COMMON = C
    R = Tier(1, '🔵', 0x55ACEE); RARE = R
    E = Tier(2, '🟣', 0xCC41CC); EPIC = E
    L = Tier(3, '🟠', 0xE0A23C); LEGENDARY = L
    M = Tier(4, '🟤', 0xFE6333); MYTHICAL = M
    D = Tier(5, '⚪', 0xFFFFFF); DIVINE = D
    P = Tier(6, '🟡', 0xFFFF33); PERK = P



class Elem(NamedTuple):
    name: str
    color: int
    emoji: str

class Element(Elem, Enum):
    EXPLOSIVE = HEAT = Elem('EXPLOSIVE', 0xb71010, STAT_NAMES['expDmg'][1])
    ELECTRIC  = ELEC = Elem('ELECTRIC',  0x106ed8, STAT_NAMES['eleDmg'][1])
    PHYSICAL  = PHYS = Elem('PHYSICAL',  0xffb800, STAT_NAMES['phyDmg'][1])
    COMBINED  = COMB = Elem('COMBINED',  0x211d1d, '🔰')
    OMNI =             Elem('OMNI',      0x000000, '<a:energyball:731885130594910219>')



class Icon(NamedTuple):
    URL: str
    emoji: str

class Icons(Icon, Enum):
    TORSO      = Icon('https://i.imgur.com/iNtSziV.png', '<:torso:730115680363347968>')
    LEGS       = Icon('https://i.imgur.com/6NBLOhU.png', '<:legs:730115699397361827>')
    DRONE      = Icon('https://i.imgur.com/oqQmXTF.png', '<:drone:730115574763618394>')
    SIDE_RIGHT = Icon('https://i.imgur.com/CBbvOnQ.png', '<:sider:730115747799629940>')
    SIDE_LEFT  = Icon('https://i.imgur.com/UuyYCrw.png', '<:sidel:730115729365663884>')
    TOP_RIGHT  = Icon('https://i.imgur.com/LW7ZCGZ.png', '<:topr:730115786735091762>')
    TOP_LEFT   = Icon('https://i.imgur.com/1xlnVgK.png', '<:topl:730115768431280238>')
    TELEPORTER = Icon('https://i.imgur.com/Fnq035A.png', '<:tele:730115603683213423>')
    CHARGE     = Icon('https://i.imgur.com/UnDqJx8.png', '<:charge:730115557239685281>')
    HOOK       = Icon('https://i.imgur.com/8oAoPcJ.png', '<:hook:730115622347735071>')
    MODULE     = Icon('https://i.imgur.com/dQR8UgN.png', '<:mod:730115649866694686>')
    SIDE_WEAPON = SIDE_RIGHT
    TOP_WEAPON = TOP_RIGHT
    CHARGE_ENGINE = CHARGE
    GRAPPLING_HOOK = HOOK
    # SHIELD            = Icon('', '')
    # PERK              = Icon('', '')
    # KIT


MAX_WEIGHT = 1010


class MechRenderer:
    layer_order = ('drone', 'side2', 'side4', 'top2', 'leg2', 'torso', 'leg1', 'top1', 'side1', 'side3')

    def __init__(self, torso: Item) -> None:
        self.torso_image = torso.image
        self.pixels_to_left = 0
        self.pixels_to_right = 0
        self.pixels_upwards = 0
        self.pixels_downwards = 0
        assert torso.attachments is not None
        self.torso_attachments = torso.attachments

        self.images: list[tuple[int, int, Image.Image] | None] = [None] * 10


    def add_image(self, item: Item, layer: str) -> None:
        if layer == 'legs':
            self.add_image(item, 'leg1')
            self.add_image(item, 'leg2')
            return

        attachment = item.attachment
        assert attachment is not None

        item_x, item_y = attachment['x'], attachment['y']

        if layer == 'drone':
            offset = Attachment(x=0, y=0)

        else:
            offset: Attachment = self.torso_attachments[layer]

        x_offset, y_offset = offset['x'], offset['y']

        x = x_offset - item_x
        y = y_offset - item_y

        self.check_offset(item, x, y)
        self.put_image(item.image, layer, x, y)


    def check_offset(self, item: Item, x: int, y: int) -> None:
        width, height = bbox_to_w_h(item.image.getbbox())
        t_width, t_height = bbox_to_w_h(self.torso_image.getbbox())

        self.pixels_to_left = max(self.pixels_to_left, max(-x, 0))
        self.pixels_upwards = max(self.pixels_upwards, max(-y, 0))
        self.pixels_to_right = max(self.pixels_to_right, max(x + width - t_width, 0))
        self.pixels_downwards = max(self.pixels_downwards, max(y + height - t_height, 0))


    def put_image(self, image: Image.Image, layer: str, x: int, y: int) -> None:
        self.images[self.layer_order.index(layer)] = (x, y, image)


    def finalize(self) -> Image.Image:
        self.put_image(self.torso_image, 'torso', 0, 0)

        width, height = bbox_to_w_h(self.torso_image.getbbox())
        width += self.pixels_to_left + self.pixels_to_right
        height += self.pixels_upwards + self.pixels_downwards

        canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        for x, y, image in filter(None, self.images):
            canvas.alpha_composite(image, (x + self.pixels_to_left, y + self.pixels_upwards))

        return canvas



class Mech:
    """Represents a mech build."""
    torso:  Item | None
    legs:   Item | None
    drone:  Item | None
    side1:  Item | None
    side2:  Item | None
    side3:  Item | None
    side4:  Item | None
    top1:   Item | None
    top2:   Item | None
    tele:   Item | None
    charge: Item | None
    hook:   Item | None
    mod1:   Item | None
    mod2:   Item | None
    mod3:   Item | None
    mod4:   Item | None
    mod5:   Item | None
    mod6:   Item | None
    mod7:   Item | None
    mod8:   Item | None

    def __init__(self):
        self._items: dict[str, Item | None] = {
            'torso':  None,
            'legs':   None,
            'drone':  None,
            'side1':  None,
            'side2':  None,
            'side3':  None,
            'side4':  None,
            'top1':   None,
            'top2':   None,
            'tele':   None,
            'charge': None,
            'hook':   None,
            'mod1':   None,
            'mod2':   None,
            'mod3':   None,
            'mod4':   None,
            'mod5':   None,
            'mod6':   None,
            'mod7':   None,
            'mod8':   None}

        self.has_modified = True
        self.stats_cache = AnyStats()
        self.items_to_load: set[Item] = set()


    def __getattr__(self, name: Any) -> Item | None:
        if name in self._items:
            return self._items[name]

        raise AttributeError(f'{type(self).__name__} object has no attribute "{name}"') from None


    def __setitem__(self, _type: AnyType | tuple[AnyType, int], value: Item | None) -> None:
        if not isinstance(value, (Item, type(None))):
            raise TypeError

        pos = None

        if isinstance(_type, tuple):
            _type, pos = _type

        item_type = _type.lower()
        self.has_modified = True

        if value is not None and value._image is None:
            self.items_to_load.add(value)

        if item_type in {'torso', 'legs', 'drone', 'teleporter', 'charge', 'charge_engine', 'hook', 'grappling_hook'}:
            self._items[item_type] = value
            return

        if pos is None:
            raise TypeError(f'"{item_type}" requires pos passed')

        if item_type == 'module':
            if not 0 < pos <= 8:
                raise ValueError(f'Pos outside range 1-8')

            self._items[f'mod{pos}'] = value

        elif item_type == 'side_weapon':
            if not 0 < pos <= 4:
                raise ValueError(f'Pos outside range 1-4')

            self._items[f'side{pos}'] = value

        elif item_type == 'top_weapon':
            if not 0 < pos <= 2:
                raise ValueError(f'Pos outside range 1-2')

            self._items[f'top{pos}'] = value

        else:
            raise TypeError('Invalid item type passed')


    def __str__(self) -> str:
        def make_str(item: Item | None) -> str:
            return '' if item is None else f'{item.type.capitalize()}: {item}'

        string_parts = [*map(make_str, (self.torso, self.legs, self.drone))]

        if weapon_string := ', '.join(f'{wep}{f" x{count}" * (count > 1)}' for wep, count in Counter(filter(None, self.iter_weapons())).items()):
            string_parts.append('Weapons: ' + weapon_string)

        string_parts.extend(map(make_str, (self.tele, self.charge, self.hook)))

        if modules := ', '.join(f'{mod}{f" x{count}" * (count > 1)}' for mod, count in Counter(filter(None, self.iter_modules())).items()):
            string_parts.append('Modules: ' + modules)

        return '\n'.join(filter(None, string_parts))


    @property
    def weight(self) -> int:
        return self.calc_stats.get('weight', 0)


    @property
    def is_valid(self) -> bool:
        return (self.torso is not None
                and self.legs is not None
                and any(wep is not None for wep in self.iter_weapons())
                and self.weight <= MAX_WEIGHT)


    @property
    def calc_stats(self) -> AnyStats:
        if self.has_modified:
            total_stats = self.stats_cache
            total_stats.clear()  # type: ignore

            for item in self.iter_items():
                if item is None:
                    continue

                for key in stat_mixin.keys():
                    if key in item.stats:
                        if key not in total_stats:
                            total_stats[key] = 0

                        total_stats[key] += item.stats[key]

            if (weight := total_stats.setdefault('weight', 0)) > 1000:
                total_stats['health'] = total_stats.get('health', 0) - (weight - 1000) * 15

            self.has_modified = False

        return self.stats_cache


    @property
    def display_stats(self) -> str:
        stats = self.calc_stats
        reference = tuple(stat_mixin.keys())
        order = sorted(stats, key=lambda item: reference.index(item))

        main_str = ''

        for stat in order:
            name, icon = STAT_NAMES[stat]
            if stat == 'weight':
                value = stats[stat]  # type: ignore

                emojis = '👽⚙️👌❗⛔'

                e = emojis[(value > 0) + (value >= 1000) + (value > 1000) + (value > MAX_WEIGHT)]

                main_str += f'{icon} **{value}** {e} {name}\n'

            else:
                main_str += f'{icon} **{stats[stat]}** {name}\n'

        return main_str


    @property
    def image(self) -> Image.Image:
        """Returns `Image` object merging all item images.
        Requires the torso to be set, otherwise raises `ValueError`"""
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
            width, height = bbox_to_w_h(self.drone.image.getbbox())
            t_width, t_height = bbox_to_w_h(self.torso.image.getbbox())
            self.drone.attachment = Attachment(x=t_width - width - 50, y=t_height - height // 2)

            canvas.add_image(self.drone, 'drone')

        return canvas.finalize()


    async def load_images(self, session: aiohttp.ClientSession) -> None:
        """Bulk loads item images"""
        coros = {item.load_image(session) for item in self.iter_items() if item is not None if item._image is None}

        if coros:
            await asyncio.wait(coros, timeout=5, return_when='ALL_COMPLETED')


    def iter_weapons(self) -> Iterator[Item | None]:
        items = self._items
        yield items['side1']
        yield items['side2']
        yield items['side3']
        yield items['side4']
        yield items['top1']
        yield items['top2']


    def iter_modules(self) -> Iterator[Item | None]:
        items = self._items
        yield items['mod1']
        yield items['mod2']
        yield items['mod3']
        yield items['mod4']
        yield items['mod5']
        yield items['mod6']
        yield items['mod7']
        yield items['mod8']


    def iter_items(self) -> Iterator[Item | None]:
        yield from self._items.values()


    def modified(self) -> None:
        self.has_modified = True



stat_mixin = dict[str, type[Union[int, tuple[int, int]]]](
    weight=int,
    health=int,
    eneCap=int,
    eneReg=int,
    heaCap=int,
    heaCol=int,
    phyRes=int,
    expRes=int,
    eleRes=int,
    bulletCap=int,
    rocketCap=int)


damage_mixin = dict[str, type[Union[int, tuple[int, int]]]](
    phyDmg=tuple[int, int],
    phyResDmg=int,
    eleDmg=tuple[int, int],
    eneDmg=int,
    eneCapDmg=int,
    eneRegDmg=int,
    eleResDmg=int,
    expDmg=tuple[int, int],
    heaDmg=int,
    heaCapDmg=int,
    heaColDmg=int,
    expResDmg=int,
    range=tuple[int, int],
    push=int,
    pull=int,
    recoil=int,
    advance=int,
    retreat=int,
    backfire=int,
    heaCost=int,
    eneCost=int,
    bulletCost=int,
    rocketCost=int)



class Item:
    """Represents a single item."""

    def __init__(
        self,
        id: int,
        name: str,
        image: str,
        type: str,
        stats: AnyStats,
        transform_range: str,
        divine: AnyStats=None,
        element: str=None,
        attachment: Attachment | Attachments | None=None,
        **kwargs: Any
        ) -> None:

        assert isinstance(name, str) and isinstance(image, str), 'Invalid type'
        self.id = id
        self.name = name
        self.partial_url = image
        self.image_url: str | None = None
        self._image: Image.Image | None = None

        self.icon = Icons[type]  # this will also validate if type is of correct type
        self.type = type
        self.stats = stats
        self.divine = divine

        val_a, _, val_b = transform_range.partition('-')
        self.rarity = (Rarity[val_a], Rarity[val_b]) if val_b else Rarity[val_a]
        self.element = Element.OMNI if element is None else Element[element]

        self.attachment = self.attachments = None
        self.kwargs = kwargs

        if attachment is not None:
            if 'x' in attachment:
                self.attachment: Attachment | None = attachment  # type: ignore

            else:
                self.attachments: Attachments | None = attachment  # type: ignore


    def __str__(self) -> str:
        return self.name


    def __repr__(self) -> str:
        return '<{0.name} - {0.element.value} {0.type} {0.rarity} {0.stats}>'.format(self)


    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Item):
            return False

        return (o.id     == self.id
            and o.name   == self.name
            and o.type   == self.type
            and o.stats  == self.stats
            and o.divine == self.divine
            and o.rarity == self.rarity)



    def __hash__(self) -> int:
        return hash(self.id)


    @property
    def image(self) -> Image.Image:
        """Returns a copy of image for this item. Before this property is ever retrieved, load_image needs to be called."""
        if self._image is None:
            raise RuntimeError('load_image was never called')

        if 'width' in self.kwargs or 'height' in self.kwargs:
            new_width, new_height = self.kwargs.get('width', 0), self.kwargs.get('height', 0)

            width, height = bbox_to_w_h(self._image.getbbox())
            width = new_width or width
            height = new_height or height

            return self._image.resize((width, height))

        return self._image.copy()


    async def load_image(self, session: aiohttp.ClientSession) -> None:
        """Loads the image from web"""
        if self.image_url is None:
            raise ValueError('Image URL was not set')

        self._image = await get_image(self.image_url, session)
