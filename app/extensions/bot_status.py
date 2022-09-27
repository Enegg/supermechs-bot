from __future__ import annotations

import random
import sys
import typing as t
from datetime import datetime

from disnake import CommandInteraction, Embed, __version__ as disnake_version
from disnake.utils import oauth_url

from app.lib_helpers import BotPlugin

if t.TYPE_CHECKING:
    from app.bot import SMBot

plugin = BotPlugin["SMBot"]()


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users"""
    frantics = [
        "https://i.imgur.com/Bbbf4AH.mp4",
        "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4",
    ]
    choice = random.choice(frantics)
    await inter.send(choice)


@plugin.slash_command()
async def ping(inter: CommandInteraction) -> None:
    """Shows bot latency."""
    await inter.response.send_message(f"Pong! {round(plugin.bot.latency * 1000)}ms", ephemeral=True)


@plugin.slash_command(name="self")
async def self_info(inter: CommandInteraction) -> None:
    """Displays information about the bot."""
    app_info = await plugin.bot.application_info()
    desc = (
        f"Member of {len(inter.bot.guilds)} server{'s' * (len(plugin.bot.guilds) != 1)}"
        f"\n**Author:** {app_info.owner.mention}"
    )

    if app_info.bot_public:
        invite = oauth_url(inter.me.id, scopes=("bot", "applications.commands"))
        desc += f"\n[**Invite link**]({invite})"

    uptime = datetime.now() - plugin.bot.started_at
    ss = uptime.seconds
    mm, ss = divmod(ss, 60)
    hh, mm = divmod(mm, 60)

    time_data: list[str] = []
    if (days := uptime.days) != 0:
        time_data.append(f'{days} day{"s" * (days != 1)}')

    if hh != 0:
        time_data.append(f"{hh}h")

    if mm != 0:
        time_data.append(f"{mm}min")

    if ss != 0:
        time_data.append(f"{ss}s")

    python_version = ".".join(map(str, sys.version_info[:3]))

    tech_field = (
        f"Python build: {python_version} {sys.version_info.releaselevel}"
        f"\ndisnake version: {disnake_version}"
        f"\nUptime: {' '.join(time_data)}"
    )

    embed = (
        Embed(title="Bot info", description=desc, color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("Technical", tech_field)
        .set_footer(text="Created")
    )
    embed.timestamp = inter.me.created_at

    await inter.send(embed=embed, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
