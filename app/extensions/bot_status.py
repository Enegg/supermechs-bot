from __future__ import annotations

import random
import sys
import typing as t

import anyio
from disnake import CommandInteraction, Embed, __version__ as disnake_version
from disnake.ext.plugins import Plugin
from disnake.utils import format_dt, oauth_url, utcnow

from assets import FRANTIC_GIFS
from config import DEFAULT_PACK, TEST_GUILDS
from events import PACK_LOADED
from library_extensions import RESPONSE_TIME_LIMIT, Markdown as MD, command_mention
from managers import item_pack_manager, player_manager
from shared.metrics import command_invocations, get_ram_utilization, get_sloc
from shared.utils import wrap_bytes

import supermechs

if t.TYPE_CHECKING:
    from disnake.ext.commands import InteractionBot  # noqa: F401

python_version = ".".join(map(str, sys.version_info[:3]))

plugin = Plugin["InteractionBot"](name="Bot-status", logger=__name__)

START_TIME = utcnow()


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(FRANTIC_GIFS)
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Displays information about the bot."""

    bot = plugin.bot
    app_info = await bot.application_info()
    app_info.team

    general_fields = [
        f"Developer: {app_info.owner.mention}",
        f"Created: {format_dt(bot.user.created_at, 'R')}",
        f"Servers: {len(bot.guilds)}",
    ]
    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(MD.hyperlink("**Invite link**", invite))

    backend_fields = [
        f"Python version: {python_version}",
        f"disnake version: {disnake_version}",
    ]
    supermechs_fields = [
        f"Registered players: {len(player_manager)}",
        f"Invoked commands: {command_invocations.total()}",
    ]
    bits, exponent = wrap_bytes(get_ram_utilization())
    perf_fields = [
        f"Started: {format_dt(START_TIME, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bits}{exponent}",
    ]
    async with anyio.move_on_after(RESPONSE_TIME_LIMIT - 0.5):
        loc = await get_sloc("app")
        loc += await get_sloc(next(iter(supermechs.__path__)))
        backend_fields.append(f"Lines of code: {loc}")

    if PACK_LOADED.is_set():
        default_pack = item_pack_manager["@Darkstare"]  # TODO
        supermechs_fields += [
            f"Default item pack: {MD.hyperlink(default_pack.key, DEFAULT_PACK)}",
            f"Total items: {len(default_pack.items)}",
        ]
    embed = (
        Embed(title="Bot info", color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("General", "\n".join(general_fields), inline=False)
        .add_field("Backend", "\n".join(backend_fields), inline=False)
        .add_field("SuperMechs", "\n".join(supermechs_fields), inline=False)
        .add_field("Performance", "\n".join(perf_fields), inline=False)
    )

    await inter.response.send_message(embed=embed, ephemeral=True)


@plugin.slash_command(guild_ids=TEST_GUILDS)
async def activity(inter: CommandInteraction) -> None:
    """Displays command invocation activity."""
    desc = (
        "\n".join(
            f"{command_mention(command)}: {invocations}"
            for command, invocations in command_invocations.items()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=START_TIME)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
