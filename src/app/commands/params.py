# pyright: enableExperimentalFeatures=true
from typing import Literal
from typing_extensions import TypedDict

from disnake import Localized, OptionChoice

from dupermechs.enums import ItemElement, ItemRarity, ItemType

__all__ = ("ELEMENT_CHOICES", "TYPE_CHOICES")

TYPE_CHOICES = (
    OptionChoice(Localized("Torso", key="CHOICE_TORSO"), ItemType.torso.name),
    OptionChoice(Localized("Legs", key="CHOICE_LEGS"), ItemType.legs.name),
    OptionChoice(Localized("Drone", key="CHOICE_DRONE"), ItemType.drone.name),
    OptionChoice(Localized("Side weapon", key="CHOICE_SIDE_WEAPON"), ItemType.side_weapon.name),
    OptionChoice(Localized("Top weapon", key="CHOICE_TOP_WEAPON"), ItemType.top_weapon.name),
    OptionChoice(Localized("Teleport", key="CHOICE_TELEPORT"), ItemType.teleport.name),
    OptionChoice(Localized("Charge Engine", key="CHOICE_CHARGE"), ItemType.charge.name),
    OptionChoice(Localized("Grappling Hook", key="CHOICE_HOOK"), ItemType.hook.name),
    OptionChoice(Localized("Shield", key="CHOICE_SHIELD"), ItemType.shield.name),
    OptionChoice(Localized("Module", key="CHOICE_MODULE"), ItemType.module.name),
    OptionChoice(Localized("Perk", key="CHOICE_PERK"), ItemType.perk.name),
)
ELEMENT_CHOICES = (
    OptionChoice(Localized("Physical", key="CHOICE_PHYS"), ItemElement.physical.name),
    OptionChoice(Localized("Explosive", key="CHOICE_EXPL"), ItemElement.explosive.name),
    OptionChoice(Localized("Electric", key="CHOICE_ELEC"), ItemElement.electric.name),
    OptionChoice(Localized("Combined", key="CHOICE_COMB"), ItemElement.combined.name),
    OptionChoice(Localized("Other", key="CHOICE_NONE"), ItemElement.other.name),
)
LEGACY_TIER_CHOICES = (
    OptionChoice(Localized("Common", key="CHOICE_C"), ItemRarity.common.name),
    OptionChoice(Localized("Rare", key="CHOICE_R"), ItemRarity.rare.name),
    OptionChoice(Localized("Epic", key="CHOICE_E"), ItemRarity.epic.name),
    OptionChoice(Localized("Legendary", key="CHOICE_L"), ItemRarity.legendary.name),
    OptionChoice(Localized("Mythical", key="CHOICE_M"), ItemRarity.mythical.name),
)
TIER_CHOICES = (
    *LEGACY_TIER_CHOICES,
    OptionChoice(Localized("Divine", key="CHOICE_D"), ItemRarity.divine.name),
    OptionChoice(Localized("Perk", key="CHOICE_P"), ItemRarity.perk.name),
)


class FilledOptions(TypedDict, total=False, closed=True):
    type: Literal[
        "torso",
        "legs",
        "drone",
        "side_weapon",
        "top_weapon",
        "teleport",
        "charge",
        "hook",
        "shield",
        "module",
        "perk",
    ]
    element: Literal["physical", "explosive", "electric", "combined", "other"]
    rarity: Literal["common", "rare", "epic", "legendary", "mythical", "divine", "perk"]
    legacy: bool
