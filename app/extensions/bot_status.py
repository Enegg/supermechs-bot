from __future__ import annotations

import random
import sys
import typing as t

from disnake import CommandInteraction, Embed, __version__ as disnake_version
from disnake.ext.plugins import Plugin
from disnake.utils import format_dt, oauth_url

from bridges import AppContext
from library_extensions import Markdown
from shared.metrics import get_ram_utilization, get_sloc

if t.TYPE_CHECKING:
    from bot import ModularBot  # noqa: F401

python_version = ".".join(map(str, sys.version_info[:3]))

plugin = Plugin["ModularBot"](name="Bot-status", logger=__name__)


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    frantics = [
        "https://i.imgur.com/Bbbf4AH.mp4",
        "https://i.gyazo.com/8f85e9df5d3b1ed16b3c81dc3bccc3e9.mp4",
    ]
    choice = random.choice(frantics)
    await inter.response.send_message(choice)


@plugin.slash_command(name="self")
async def info(inter: CommandInteraction, context: AppContext) -> None:
    """Displays information about the bot."""

    bot = plugin.bot
    app_info = await bot.application_info()

    general_fields = [
        f"Python version: {python_version}",
        f"disnake version: {disnake_version}",
        f"Created: {format_dt(bot.user.created_at, 'R')}",
        f"Author: {app_info.owner.mention}",
    ]

    activity_fields = [
        f"Servers: {len(bot.guilds)}",
        f"Registered players: {len(context.client.state._players)}",
        f"Invoked commands: {bot.command_invocations.total()}",
    ]

    bits, exponent = get_ram_utilization()

    perf_fields = [
        f"Started: {format_dt(bot.started_at, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bits}{exponent}",
        f"Lines of code: {get_sloc()}",
    ]

    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(Markdown.hyperlink("**Invite link**", invite))

    embed = (
        Embed(title="Bot info", color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("General", "\n".join(general_fields))
        .add_field("Activity", "\n".join(activity_fields))
        .add_field("Performance", "\n".join(perf_fields))
    )

    await inter.response.send_message(embed=embed, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
