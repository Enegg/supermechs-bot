import disnake
from discord.ui.store import InteractionCallback
from disnake import MessageInteraction

from app import i18n


def get_check(user: disnake.abc.User, /) -> InteractionCallback[bool]:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == user.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return interaction_check
