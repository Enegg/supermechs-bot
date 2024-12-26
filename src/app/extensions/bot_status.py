import random

from discord import markdown as md
from disnake import CommandInteraction, Embed
from disnake.ext import commands
from disnake.utils import oauth_url
from disnake_plugins import Plugin

from app import meta
from app.assets import ASSETS
from app.async_utils import amap, move_on_before_timeout
from app.bridges import get_ram_utilization, get_sloc, invoke_counter
from app.core import CONFIG
from app.local_storage import players
from app.state import state
from app.utils import fold_binary_prefix

import supermechs

plugin = Plugin[commands.InteractionBot](name="Bot-status", logger="ext")


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.gifs["frantics"])
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    bot = plugin.bot
    app_info = await bot.application_info()

    general_fields = [
        f"Developer: {app_info.owner.mention}",
        f"Created: {md.format_dt(bot.user.created_at, 'R')}",
        f"Servers: {len(bot.guilds)}",
        f"Invoked commands: {invoke_counter.total()}",
    ]
    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(md.hyperlink("**Invite link**", invite))

    backend_fields = [
        f"Python version: {meta.python_version}",
        f"Discord library: {md.hyperlink('disnake', meta.disnake_url)} {meta.disnake_version}",
    ]
    supermechs_fields = [
        f"Registered players: {len(players.mapping)}",
        f"Default item pack: {md.hyperlink(state.item_pack.key, CONFIG.default_pack_url)}",
        f"Total items: {len(state.item_pack.items)}",
    ]
    bytes_, prefix = fold_binary_prefix(get_ram_utilization())
    perf_fields = [
        f"Started: {md.format_dt(meta.started_at, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bytes_}{prefix}B",
    ]
    with move_on_before_timeout():
        app_loc, sm_loc = await amap(get_sloc, "src", *supermechs.__path__)
        backend_fields.append(f"Lines of code: {app_loc} bot, {sm_loc} SM library")

    embed = (
        Embed(title="Bot info", color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("General", "\n".join(general_fields), inline=False)
        .add_field("Backend", "\n".join(backend_fields), inline=False)
        .add_field("SuperMechs", "\n".join(supermechs_fields), inline=False)
        .add_field("Performance", "\n".join(perf_fields), inline=False)
    )
    await inter.response.send_message(embed=embed, ephemeral=True)


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def activity(inter: CommandInteraction) -> None:
    """Display command invocation activity."""
    desc = (
        "\n".join(
            f"{md.command_mention(command)}: {invocations}"
            for command, invocations in invoke_counter.items()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=meta.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
