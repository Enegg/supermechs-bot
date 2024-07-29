from app import i18n
from discord_plus.ui.store import InteractionCallback

import disnake
from disnake import MessageInteraction


def get_check(user: disnake.abc.User, /) -> InteractionCallback[bool]:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == user.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return interaction_check
