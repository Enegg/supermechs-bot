import random
import typing

import anyio
from disnake import CommandInteraction, Embed
from disnake.ext import commands, plugins
from disnake.utils import format_dt, oauth_url

import meta
from assets import FRANTIC_GIFS
from config import DEFAULT_PACK_KEY, DEFAULT_PACK_URL, TEST_GUILDS
from events import DEFAULT_PACK_LOADED
from library_extensions import RESPONSE_TIME_LIMIT, Markdown as MD, command_mention
from shared.item_packs import get_default_pack
from shared.metrics import command_invocations, get_ram_utilization, get_sloc
from shared.utils import fold_binary_prefix
from stored import players

import supermechs

plugin: typing.Final = plugins.Plugin[commands.InteractionBot](name="Bot-status", logger=__name__)


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
    async with anyio.move_on_after(RESPONSE_TIME_LIMIT - 0.5):
        app_loc = await get_sloc("app")
        sm_loc = await get_sloc(next(iter(supermechs.__path__)))
        backend_fields.append(f"Lines of code: {app_loc} bot, {sm_loc} SM library")

    if DEFAULT_PACK_LOADED.is_set():
        default_pack = get_default_pack()
        supermechs_fields += [
            f"Default item pack: {MD.hyperlink(default_pack.key, DEFAULT_PACK_URL)}",
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

    embed = Embed(title="Command activity", description=desc, timestamp=meta.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
