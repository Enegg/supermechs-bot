from __future__ import annotations

import typing as t
from functools import partial

from disnake import MessageInteraction
from disnake.ui.item import Item

if t.TYPE_CHECKING:
    from .views import V_CO

else:
    V_CO = t.NewType("V_CO", t.Any)

I_CO = t.TypeVar("I_CO", bound=Item, covariant=True)
I = t.TypeVar("I", bound=Item)

Callback = t.Callable[[I_CO, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]
ItemCallbackType = t.Callable[[V_CO, I_CO, MessageInteraction], t.Coroutine[t.Any, t.Any, t.Any]]

__all__ = ("add_callback", "Item", "I_CO", "I")


def add_callback(item: I, callback: Callback[I]) -> I:
    item.callback = partial(callback, item)
    return item
