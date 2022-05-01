from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from .inv_item import InvItem


class GameError(Exception):
    """Base class for game related errors"""


class MaxPowerReached(GameError):
    """Exception raised when attempting to add power to an already maxed item"""

    def __init__(self, item: InvItem) -> None:
        """Exception raised when attempting to add power to an already maxed item"""
        super().__init__(f"Maximum power for item {item.name} reached")


class MaxTierReached(GameError):
    """Exception raised when attempting to transform an item at max tier"""

    def __init__(self, item: InvItem) -> None:
        """Exception raised when attempting to transform an item at max tier"""
        super().__init__(f"Maximum tier for item {item.name} reached")
