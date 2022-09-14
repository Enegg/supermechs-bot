from __future__ import annotations

import logging
import random
import sys
import typing as t
from datetime import datetime

from disnake import CommandInteraction, Embed
from disnake import __version__ as disnake_version
from disnake.ext import commands
from disnake.utils import oauth_url

if t.TYPE_CHECKING:
    from app.bot import SMBot

logger = logging.getLogger(f"main.{__name__}")


@commands.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users"""
    frantics = [
        "https://i.imgur.com/Bbbf4AH.mp4",
        "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4",
    ]
    choice = random.choice(frantics)
    await inter.send(choice)


class Misc(commands.Cog):
    def __init__(self, bot: SMBot) -> None:
        self.bot = bot

    @commands.slash_command()
    async def ping(self, inter: CommandInteraction) -> None:
        """Shows bot latency"""
        await inter.send(f"Pong! {round(self.bot.latency * 1000)}ms")

    @commands.slash_command(name="self")
    async def self_info(self, inter: CommandInteraction) -> None:
        """Displays information about the bot."""
        app = await self.bot.application_info()
        desc = (
            f"Member of {len(inter.bot.guilds)} server{'s' * (len(self.bot.guilds) != 1)}"
            f"\n**Author:** {app.owner.mention}"
        )

        if app.bot_public:
            invite = oauth_url(inter.me.id, scopes=("bot", "applications.commands"))
            desc += f"\n[**Invite link**]({invite})"

        uptime = datetime.now() - self.bot.run_time
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


def setup(bot: SMBot) -> None:
    bot.add_slash_command(frantic)
    bot.add_cog(Misc(bot))
