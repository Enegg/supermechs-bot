import random
from functools import partial
from typing import NamedTuple

import disnake
from app.disnake_types import CommandInteraction
from discord import markdown as md
from discord.null_objects import NullUser
from disnake import Embed
from disnake.ext import tasks
from disnake.utils import oauth_url

from app import meta, ui
from app.assets import ASSETS, EMOJIS
from app.async_utils import gather
from app.commands import telemetry
from app.core import CONFIG
from app.devtools import debug_message
from app.managers import packs, players
from app.plugins_factory import create_plugin
from app.system import get_ram_usage, get_sloc
from app.utils import as_binary_unit
from resources import HttpResource

plugin = create_plugin(__name__)


class _BotInfo(NamedTuple):
    owner: disnake.abc.User = NullUser()
    app_sloc: int = 0
    bot_public: bool = False


_bot_info: _BotInfo = _BotInfo()


@plugin.register_loop(wait_until_ready=True)
@tasks.loop(count=1)
async def load_info() -> None:
    global _bot_info
    app_info, app_sloc = await gather(
        plugin.bot.application_info,
        partial(get_sloc, "src"),
    )
    _bot_info = _BotInfo(
        owner=app_info.owner,
        app_sloc=app_sloc,
        bot_public=app_info.bot_public,
    )


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.frantic_gifs)
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    bot = plugin.bot

    components: ui.MessageComponents = []
    general_fields = [
        f"Developer: {_bot_info.owner.mention}",
        f"Created: {md.format_dt(bot.user.created_at, 'R')}",
        f"Servers: {len(bot.guilds)}",
    ]
    if _bot_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        components.append(ui.UrlButton(url=invite, label="Invite me!", emoji=EMOJIS.types.drone))

    backend_fields = [
        f"Python version: {meta.python_version}",
        f"Discord library: {md.hyperlink('disnake', meta.disnake_url)} {meta.disnake_version}",
        f"Lines of code: {_bot_info.app_sloc}",
    ]

    metadata = packs.get_item_pack_metadata()
    pack_key = (metadata.key or metadata.name).unwrap_or("<unknown>")

    if isinstance(CONFIG.item_pack_uri, HttpResource):
        pack_key = md.hyperlink(pack_key, CONFIG.item_pack_uri.uri)

    item_pack = packs.get_item_pack()
    supermechs_fields = [
        f"Registered players: {len(players.PLAYER_MAPPING)}",
        f"Item pack: {pack_key}",
        f"Total items: {len(item_pack.reloaded_items)} reloaded, {len(item_pack.legacy_items)} legacy",
    ]
    bytes_, prefix = as_binary_unit(get_ram_usage())
    perf_fields = [
        f"Started: {md.format_dt(meta.started_at, 'R')}",
        f"Invoked commands: {telemetry.total_invocations()}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bytes_}{prefix}B",
    ]

    embed = (
        Embed(title="Bot info", color=inter.me.color)
        .set_thumbnail(inter.me.display_avatar.url)
        .add_field("General", "\n".join(general_fields), inline=False)
        .add_field("SuperMechs", "\n".join(supermechs_fields), inline=False)
        .add_field("Backend", "\n".join(backend_fields), inline=False)
        .add_field("Performance", "\n".join(perf_fields), inline=False)
    )
    if CONFIG.indev:
        debug_message(embed, components)

    await inter.response.send_message(embed=embed, components=components, ephemeral=True)


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def activity(inter: CommandInteraction) -> None:
    """Display command invocation activity."""
    api_commands = (
        inter.bot._connection._global_application_commands  # pyright: ignore[reportPrivateUsage]
        or inter.bot._connection._guild_application_commands[CONFIG.home_guild_id]  # pyright: ignore[reportPrivateUsage]
    )

    def _get_mention(id: int) -> str:
        command = api_commands.get(id)
        if command is None:
            return str(id)

        return md.command_mention(command)

    desc = (
        "\n".join(
            f"- {_get_mention(id)}: {invocations.total}"
            for id, invocations in telemetry.iter_invocations()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=meta.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
