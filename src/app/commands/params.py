# pyright: enableExperimentalFeatures=true
from typing_extensions import TypedDict

from disnake import Localized, OptionChoice

from supermechs.enums import ItemElement, ItemRarity, ItemSlot

__all__ = ("ELEMENT_CHOICES", "SLOT_CHOICES")

SLOT_CHOICES = (
    OptionChoice(Localized("Torso", key="CHOICE_TORSO"), ItemSlot.torso.name),
    OptionChoice(Localized("Legs", key="CHOICE_LEGS"), ItemSlot.legs.name),
    OptionChoice(Localized("Drone", key="CHOICE_DRONE"), ItemSlot.drone.name),
    OptionChoice(Localized("Side weapon", key="CHOICE_SIDE_WEAPON"), ItemSlot.side_weapon.name),
    OptionChoice(Localized("Top weapon", key="CHOICE_TOP_WEAPON"), ItemSlot.top_weapon.name),
    OptionChoice(Localized("Teleport", key="CHOICE_TELEPORT"), ItemSlot.teleport.name),
    OptionChoice(Localized("Charge Engine", key="CHOICE_CHARGE"), ItemSlot.charge.name),
    OptionChoice(Localized("Grappling Hook", key="CHOICE_HOOK"), ItemSlot.hook.name),
    OptionChoice(Localized("Shield", key="CHOICE_SHIELD"), ItemSlot.shield.name),
    OptionChoice(Localized("Module", key="CHOICE_MODULE"), ItemSlot.module.name),
    OptionChoice(Localized("Perk", key="CHOICE_PERK"), ItemSlot.perk.name),
)
ELEMENT_CHOICES = (
    OptionChoice(Localized("Physical", key="CHOICE_PHYS"), ItemElement.physical.name),
    OptionChoice(Localized("Explosive", key="CHOICE_EXPL"), ItemElement.explosive.name),
    OptionChoice(Localized("Electric", key="CHOICE_ELEC"), ItemElement.electric.name),
    OptionChoice(Localized("Combined", key="CHOICE_COMB"), ItemElement.combined.name),
    OptionChoice(Localized("Other", key="CHOICE_NONE"), ItemElement.other.name),
)
LEGACY_ELEMENT_CHOICES = (*ELEMENT_CHOICES[:3], ELEMENT_CHOICES[-1])
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
    slot: str
    element: str
    rarity: str
