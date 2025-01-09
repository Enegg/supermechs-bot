from disnake import Localized, OptionChoice

from supermechs.all import ItemElementName, ItemTypeName

__all__ = ("ELEMENT_CHOICES", "TYPE_CHOICES")

TYPE_CHOICES = (
    OptionChoice(Localized("Torso", key="CHOICE_TORSO"), ItemTypeName.TORSO),
    OptionChoice(Localized("Legs", key="CHOICE_LEGS"), ItemTypeName.LEGS),
    OptionChoice(Localized("Drone", key="CHOICE_DRONE"), ItemTypeName.DRONE),
    OptionChoice(Localized("Side weapon", key="CHOICE_SIDE_WEAPON"), ItemTypeName.SIDE_WEAPON),
    OptionChoice(Localized("Top weapon", key="CHOICE_TOP_WEAPON"), ItemTypeName.TOP_WEAPON),
    OptionChoice(Localized("Teleport", key="CHOICE_TELEPORT"), ItemTypeName.TELEPORT),
    OptionChoice(Localized("Charge", key="CHOICE_CHARGE"), ItemTypeName.CHARGE),
    OptionChoice(Localized("Hook", key="CHOICE_HOOK"), ItemTypeName.HOOK),
    OptionChoice(Localized("Shield", key="CHOICE_SHIELD"), ItemTypeName.SHIELD),
    OptionChoice(Localized("Module", key="CHOICE_MODULE"), ItemTypeName.MODULE),
    OptionChoice(Localized("Any", key="CHOICE_TYPE_ANY"), "ANY"),
)
ELEMENT_CHOICES = (
    OptionChoice(Localized("Physical", key="CHOICE_PHYS"), ItemElementName.PHYSICAL),
    OptionChoice(Localized("Explosive", key="CHOICE_EXPL"), ItemElementName.EXPLOSIVE),
    OptionChoice(Localized("Electric", key="CHOICE_ELEC"), ItemElementName.ELECTRIC),
    OptionChoice(Localized("Combined", key="CHOICE_COMB"), "COMBINED"),
    OptionChoice(Localized("Any", key="CHOICE_ELEMENT_ANY"), "ANY"),
)
