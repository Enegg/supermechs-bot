"""Module extending the library provided UI kit."""

from functools import partial
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
    "callback_store",
)

CallbackStore: TypeAlias = _CallbackStore[MessageInteraction]
MessageComponents: TypeAlias = Components[MessageUIComponent]


def callback_store(base_inter: disnake.Interaction, /) -> CallbackStore:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == base_inter.author.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return _CallbackStore(
        partial(base_inter.bot.wait_for, disnake.Event.message_interaction), check=interaction_check
    )
