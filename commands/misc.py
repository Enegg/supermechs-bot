from __future__ import annotations

import logging
import random
import sys
import typing as t
from datetime import datetime

import disnake
import lib_types
from disnake.ext import commands

if t.TYPE_CHECKING:
    from bot import SMBot

logger = logging.getLogger("channel_logs")


@commands.slash_command()
async def frantic(inter: lib_types.ApplicationCommandInteraction) -> None:
    """Humiliate frantic users"""
    frantics = [
        "https://i.imgur.com/Bbbf4AH.mp4",
        "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4"
    ]
    choice = random.choice(frantics)
    await inter.send(choice)


class Misc(commands.Cog):
    @commands.slash_command()
    async def ping(self, inter: lib_types.ApplicationCommandInteraction) -> None:
        """Shows bot latency"""
        await inter.send(f'Pong! {round(inter.bot.latency * 1000)}ms')

    @commands.slash_command()
    async def invite(self, inter: lib_types.ApplicationCommandInteraction) -> None:
        """Sends an invite link for this bot to the channel"""
        await inter.send(
            disnake.utils.oauth_url(inter.bot.user.id, scopes=("bot", "applications.commands"))
        )

    @commands.slash_command(name="self")
    async def self_info(self, inter: lib_types.ApplicationCommandInteraction) -> None:
        """Displays information about the bot."""
        app = await inter.bot.application_info()
        desc = (
            f'Member of {len(inter.bot.guilds)} server{"s" * (len(inter.bot.guilds) != 1)}'
            f"\n**Author:** {app.owner.mention}")

        if app.bot_public:
            invite = disnake.utils.oauth_url(inter.bot.user.id, scopes=("bot", "applications.commands"))
            desc += f"\n[**Invite link**]({invite})"

        uptime = datetime.now() - inter.bot.run_time
        ss = uptime.seconds
        mm, ss = divmod(ss, 60)
        hh, mm = divmod(mm, 60)

        time_data: list[str] = []
        if uptime.days != 0:
            time_data.append(f'{uptime.days} day{"s" * (uptime.days != 1)}')

        if hh != 0:
            time_data.append(f"{hh}h")

        if mm != 0:
            time_data.append(f"{mm}min")

        if ss != 0:
            time_data.append(f"{ss}s")

        python_version = '.'.join(map(str, sys.version_info[:3]))

        tech_field = (
            f"Python build: {python_version} {sys.version_info.releaselevel}"
            f"\ndisnake version: {disnake.__version__}"
            f"\nUptime: {' '.join(time_data)}"
        )

        embed = (
            disnake.Embed(title="Bot info", description=desc, color=inter.me.color)
            .set_thumbnail(url=inter.bot.user.display_avatar.url)
            .add_field(name="Technical", value=tech_field)
            .set_footer(text="Created")
        )
        embed.timestamp = inter.me.created_at

        await inter.send(embed=embed, ephemeral=True)


def setup(bot: SMBot) -> None:
    bot.add_slash_command(frantic)
    bot.add_cog(Misc())
