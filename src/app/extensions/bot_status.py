import datetime
import random
import sys
from functools import partial
from typing import Final, NamedTuple

import disnake
from app.disnake_types import CommandInteraction
from discord import markdown as md
from discord.null_objects import NullUser
from disnake import Embed, __version__ as disnake_version
from disnake.utils import oauth_url

from app import ui
from app.assets import ASSETS, EMOJIS
from app.async_utils import gather
from app.core import CONFIG
from app.devtools import debug_message
from app.managers import packs
from app.plugins_factory import create_plugin
from app.system import get_ram_usage, get_sloc, get_start_dt
from app.utils import as_binary_unit
from resources import HttpResource

plugin = create_plugin(__name__)

python_version: Final = ".".join(map(str, sys.version_info[:3]))
disnake_url: Final = "https://github.com/DisnakeDev/disnake"
started_at: datetime.datetime = get_start_dt()


class _BotInfo(NamedTuple):
    owner: disnake.abc.User = NullUser()
    app_sloc: int = 0
    bot_public: bool = False


_bot_info: _BotInfo = _BotInfo()


@plugin.load_hook(post=True)
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
        f"Python version: {python_version}",
        f"Discord library: {md.hyperlink('disnake', disnake_url)} {disnake_version}",
        f"Lines of code: {_bot_info.app_sloc}",
    ]

    metadata = packs.get_item_pack_metadata()
    pack_key = (metadata.key or metadata.name).unwrap_or("Unnamed pack")

    if isinstance(CONFIG.item_pack_uri, HttpResource):
        pack_key = md.hyperlink(pack_key, CONFIG.item_pack_uri.uri)

    item_pack = packs.get_item_pack()
    supermechs_fields = [
        f"Item pack: {pack_key}",
        f"Total items: {len(item_pack.reloaded_items)} reloaded, {len(item_pack.legacy_items)} legacy",
    ]
    bytes_, prefix = as_binary_unit(get_ram_usage())
    perf_fields = [
        f"Started: {md.format_dt(started_at, 'R')}",
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


setup, teardown = plugin.create_extension_handlers()
