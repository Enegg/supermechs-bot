"""Module extending the library provided UI kit."""
# pyright: reportUnusedImport=false
# ruff: noqa: F401

from collections import abc
from typing import TypeAlias

import disnake
from disnake import ButtonStyle, MessageInteraction, SelectOption, TextInputStyle
from disnake.ui import Components, MessageUIComponent, Modal, StringSelect, TextInput
from ui_store import CallbackStore as _CallbackStore

from app import i18n

from .buttons import ActionButton, ToggleButton, UrlButton
from .helpers import Paginator
from .selects import PaginatedSelect

__all__ = (
    "ActionButton",
    "ButtonStyle",
    "CallbackStore",
    "MessageComponents",
    "MessageInteraction",
    "Modal",
    "PaginatedSelect",
    "Paginator",
    "SelectOption",
    "StringSelect",
    "TextInput",
    "TextInputStyle",
    "ToggleButton",
    "UrlButton",
    "get_check",
)

CallbackStore: TypeAlias = _CallbackStore[MessageInteraction]
MessageComponents: TypeAlias = Components[MessageUIComponent]


def get_check(user: disnake.abc.User, /) -> abc.Callable[[MessageInteraction], abc.Awaitable[bool]]:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == user.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return interaction_check
