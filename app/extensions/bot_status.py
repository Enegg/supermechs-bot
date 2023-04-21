from __future__ import annotations

import random
import sys
import typing as t

from disnake import CommandInteraction, Embed, __version__ as disnake_version
from disnake.ext.plugins import Plugin
from disnake.utils import format_dt, oauth_url

from bridges import AppContext
from config import TEST_GUILDS
from library_extensions import Markdown
from shared.metrics import get_ram_utilization, get_sloc
from shared.utils import wrap_bytes

from SuperMechs.urls import PACK_V2

if t.TYPE_CHECKING:
    from library_extensions.bot import ModularBot  # noqa: F401

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


@plugin.slash_command()
async def info(inter: CommandInteraction, context: AppContext) -> None:
    """Displays information about the bot."""

    bot = plugin.bot
    client = context.client
    app_info = await bot.application_info()

    general_fields = [
        f"Python version: {python_version}",
        f"disnake version: {disnake_version}",
        f"Created: {format_dt(bot.user.created_at, 'R')}",
        f"Developer: {app_info.owner.mention}",
        f"Servers: {len(bot.guilds)}",
    ]

    supermechs_fields = [
        f"Registered players: {len(client.state._players)}",
        f"Invoked commands: {bot.command_invocations.total()}",
        f"Default item pack: {Markdown.hyperlink(client.default_pack.key, PACK_V2)}",
        f"Total items: {len(client.default_pack.items)}",
    ]

    bits, exponent = wrap_bytes(get_ram_utilization())

    perf_fields = [
        f"Started: {format_dt(bot.started_at, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bits}{exponent}",
        f"Lines of code: {await get_sloc()}",
    ]

    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(Markdown.hyperlink("**Invite link**", invite))

    embed = (
        Embed(title="Bot info", color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("General", "\n".join(general_fields), inline=False)
        .add_field("SuperMechs", "\n".join(supermechs_fields), inline=False)
        .add_field("Performance", "\n".join(perf_fields), inline=False)
    )

    await inter.response.send_message(embed=embed, ephemeral=True)


@plugin.slash_command(guild_ids=TEST_GUILDS)
async def activity(inter: CommandInteraction) -> None:
    """Displays command invocation activity."""
    desc = (
        "\n".join(
            f"{command_mention}: {invocations}"
            for command_mention, invocations in plugin.bot.command_invocations.items()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=plugin.bot.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
