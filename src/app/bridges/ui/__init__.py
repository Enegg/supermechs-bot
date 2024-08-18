"""Module extending the library provided UI kit."""

from collections import abc

import disnake
from disnake import MessageInteraction

from app import i18n

from .buttons import *
from .helpers import *
from .selects import *


def get_check(user: disnake.abc.User, /) -> abc.Callable[[MessageInteraction], abc.Awaitable[bool]]:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == user.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return interaction_check
