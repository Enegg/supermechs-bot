import enum


class ItemSlot(enum.Enum):
    __slots__ = ()

    torso = enum.auto()
    legs = enum.auto()
    drone = enum.auto()
    side_weapon = enum.auto()
    top_weapon = enum.auto()
    charge = enum.auto()
    teleport = enum.auto()
    hook = enum.auto()
    shield = enum.auto()
    module = enum.auto()
    perk = enum.auto()
    kit = enum.auto()


class ItemElement(enum.Enum):
    __slots__ = ()

    other = enum.auto()
    physical = enum.auto()
    explosive = enum.auto()
    electric = enum.auto()
    combined = enum.auto()


class ItemRarity(enum.IntEnum):
    __slots__ = ()

    common = enum.auto()
    rare = enum.auto()
    epic = enum.auto()
    legendary = enum.auto()
    mythical = enum.auto()
    divine = enum.auto()
    perk = enum.auto()


class ItemSubtype(enum.Enum):
    __slots__ = ()

    none = enum.auto()
    power_kit = enum.auto()
    color_kit = enum.auto()
    transform_relic = enum.auto()
    ascension_relic = enum.auto()
    torso_perk = enum.auto()
    giant_perk = enum.auto()
    tiny_perk = enum.auto()
    hat_perk = enum.auto()
    shot_perk = enum.auto()
    melee_weapon = enum.auto()


class ItemStat(enum.StrEnum):
    __slots__ = ()

    weight = enum.auto()
    hit_points = enum.auto()
    energy_capacity = enum.auto()
    energy_regeneration = enum.auto()
    heat_capacity = enum.auto()
    heat_cooling = enum.auto()
    physical_resistance = enum.auto()
    explosive_resistance = enum.auto()
    electric_resistance = enum.auto()
    bullets_capacity = enum.auto()
    rockets_capacity = enum.auto()
    walk = enum.auto()
    jump = enum.auto()
    physical_damage = enum.auto()
    physical_resistance_damage = enum.auto()
    electric_damage = enum.auto()
    energy_damage = enum.auto()
    energy_capacity_damage = enum.auto()
    regeneration_damage = enum.auto()
    electric_resistance_damage = enum.auto()
    explosive_damage = enum.auto()
    heat_damage = enum.auto()
    heat_capacity_damage = enum.auto()
    cooling_damage = enum.auto()
    explosive_resistance_damage = enum.auto()
    range = enum.auto()
    push = enum.auto()
    pull = enum.auto()
    recoil = enum.auto()
    advance = enum.auto()
    retreat = enum.auto()
    uses = enum.auto()
    backfire = enum.auto()
    repair = enum.auto()
    heat_generation = enum.auto()
    energy_cost = enum.auto()
    bullets_cost = enum.auto()
    rockets_cost = enum.auto()
    hit_points_per_block = enum.auto()
    energy_per_block = enum.auto()
    heat_per_block = enum.auto()
    block_percentage = enum.auto()


class ArenaShopCategory(enum.StrEnum):
    __slots__ = ()

    energy_capacity = enum.auto()
    energy_regeneration = enum.auto()
    energy_damage = enum.auto()
    heat_capacity = enum.auto()
    heat_cooling = enum.auto()
    heat_damage = enum.auto()
    physical_damage = enum.auto()
    explosive_damage = enum.auto()
    electric_damage = enum.auto()
    physical_resistance = enum.auto()
    explosive_resistance = enum.auto()
    electric_resistance = enum.auto()
    fuel_capacity = enum.auto()
    fuel_regeneration = enum.auto()
    total_hp = enum.auto()
    damage_vs_titans = enum.auto()
    backfire_reduction = enum.auto()
