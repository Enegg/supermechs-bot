from __future__ import annotations

import random
import sys
import typing as t

from disnake import CommandInteraction, Embed, __version__ as disnake_version
from disnake.ext.plugins import Plugin
from disnake.utils import format_dt, oauth_url

from library_extensions import Markdown

if t.TYPE_CHECKING:
    from bot import SMBot

python_version = ".".join(map(str, sys.version_info[:3]))

plugin = Plugin["SMBot"](name="Bot-status", logger=__name__)


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    frantics = [
        "https://i.imgur.com/Bbbf4AH.mp4",
        "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4",
    ]
    choice = random.choice(frantics)
    await inter.response.send_message(choice)


@plugin.slash_command()
async def ping(inter: CommandInteraction) -> None:
    """Shows bot latency."""
    await inter.response.send_message(f"Pong! {round(plugin.bot.latency * 1000)}ms", ephemeral=True)


@plugin.slash_command(name="self")
async def self_info(inter: CommandInteraction) -> None:
    """Displays information about the bot."""

    bot = plugin.bot
    app_info = await bot.application_info()

    guild_count = len(bot.guilds)
    desc_fields = [
        f"Member of {guild_count} server{'s' * (guild_count != 1)}",
        f"Author: {app_info.owner.mention}",
    ]

    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        desc_fields.append(Markdown.hyperlink("**Invite link**", invite))

    tech_fields = [
        f"Python version: {python_version}",
        f"disnake version: {disnake_version}",
        f"Created: {format_dt(bot.user.created_at, 'R')}",
        f"Started: {format_dt(bot.started_at, 'R')}",
    ]

    embed = (
        Embed(title="Bot info", description="\n".join(desc_fields), color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("Technical", "\n".join(tech_fields))
    )

    await inter.response.send_message(embed=embed, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
