import random
import typing

from discord import Markdown as MD, command_mention

from app import meta
from app.assets import ASSETS
from app.async_utils import amap, move_on_before_timeout
from app.core import CONFIG, ENV
from app.shared.item_packs import DEFAULT_PACK
from app.shared.metrics import command_invocations, get_ram_utilization, get_sloc
from app.shared.utils import fold_binary_prefix
from app.stored import players

from disnake import CommandInteraction, Embed
from disnake.ext import commands, plugins
from disnake.utils import format_dt, oauth_url

import supermechs

plugin: typing.Final = plugins.Plugin[commands.InteractionBot](name="Bot-status", logger=__name__)


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.gifs["frantics"])
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Displays information about the bot."""

    bot = plugin.bot
    app_info = await bot.application_info()

    general_fields = [
        f"Developer: {app_info.owner.mention}",
        f"Created: {format_dt(bot.user.created_at, 'R')}",
        f"Servers: {len(bot.guilds)}",
        f"Invoked commands: {command_invocations.total()}",
    ]
    if app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(MD.hyperlink("**Invite link**", invite))

    backend_fields = [
        f"Python version: {meta.python_version}",
        f"Discord library: {MD.hyperlink('disnake', meta.disnake_url)} {meta.disnake_version}",
    ]
    supermechs_fields = [
        f"Registered players: {len(players.mapping)}",
    ]
    bytes_, prefix = fold_binary_prefix(get_ram_utilization())
    perf_fields = [
        f"Started: {format_dt(meta.started_at, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bytes_}{prefix}B",
    ]
    with move_on_before_timeout():
        app_loc, sm_loc = await amap(get_sloc, "app", *supermechs.__path__)
        backend_fields.append(f"Lines of code: {app_loc} bot, {sm_loc} SM library")

    if DEFAULT_PACK.is_set():
        default_pack = DEFAULT_PACK.get_nowait()
        supermechs_fields += [
            f"Default item pack: {MD.hyperlink(default_pack.data.key, CONFIG.default_pack_url)}",
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


@plugin.slash_command(guild_ids=ENV.test_guild_ids)
async def activity(inter: CommandInteraction) -> None:
    """Displays command invocation activity."""
    desc = (
        "\n".join(
            f"{command_mention(command)}: {invocations}"
            for command, invocations in command_invocations.items()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=meta.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
