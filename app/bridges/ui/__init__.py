import disnake
from disnake import Locale, MessageInteraction, SelectOption

import i18n
from discord_extensions.ui.store import InteractionCallback


def make_empty_option(locale: Locale, /) -> SelectOption:
    return SelectOption(
        label=i18n.get_message(locale, "ui-empty-option-label"),
        description=i18n.get_message(locale, "ui-empty-option-desc"),
        value="$empty",
        emoji="🗑️",
    )


def get_check(user: disnake.abc.User, /) -> InteractionCallback[bool]:
    async def interaction_check(inter: MessageInteraction, /) -> bool:
        if inter.author.id == user.id:
            return True

        msg = i18n.get_message(inter.locale, "ui-disallowed")
        await inter.send(msg, ephemeral=True)
        return False

    return interaction_check
