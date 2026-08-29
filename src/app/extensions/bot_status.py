import random
import sys
from functools import partial
from typing import Final, NamedTuple

import disnake
from app.disnake_types import CommandInteraction
from discord import MessageBuilder, markdown as md
from discord.null_objects import NullUser
from disnake import __version__ as disnake_version
from disnake.utils import oauth_url

from app import ui
from app.assets import ASSETS, EMOJIS
from app.async_utils import gather
from app.core import CONFIG
from app.devtools import debug_components
from app.managers import packs
from app.plugins_factory import create_plugin
from app.system import BOT_PROCESS, get_ram_usage, get_sloc
from app.utils import as_binary_unit
from resources import HttpResource

plugin = create_plugin(__name__)

python_version: Final = ".".join(map(str, sys.version_info[:3]))
disnake_url: Final = "https://github.com/DisnakeDev/disnake"


class _BotInfo(NamedTuple):
    owner: disnake.abc.User = NullUser()
    app_sloc: int = 0
    bot_public: bool = False


_bot_info: _BotInfo = _BotInfo()


@plugin.load_hook(post=True)
async def _() -> None:
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


@plugin.slash_command(name="frantic")
async def slash_frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.frantic_gifs)
    await inter.response.send_message(choice)


@plugin.slash_command(name="info")
async def slash_info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    bot = plugin.bot

    builder = MessageBuilder()
    add_component = builder.nested_component(ui.container(accent_color=inter.me.color))
    add_component(ui.Section(
        ui.TextDisplay(
            "## Bot info\n"
            "**General**\n"
            f"Developer: {_bot_info.owner.mention}\n"
            f"Created: {md.format_dt(bot.user.created_at, 'R')}\n"
            f"Servers: {len(bot.guilds)}"
        ),
        accessory=ui.thumbnail(inter.me.display_avatar),
    ))  # fmt: skip

    pack_key = "Built-in items pack"

    if isinstance(CONFIG.item_pack_uri, HttpResource):
        pack_key = md.hyperlink(pack_key, CONFIG.item_pack_uri.uri)

    item_pack = packs.get_item_pack()
    add_component(ui.TextDisplay(
        "**SuperMechs**\n"
        f"Item pack: {pack_key}\n"
        f"Total items: {len(item_pack.reloaded_items)} reloaded, {len(item_pack.legacy_items)} legacy"
    ))  # fmt: skip
    add_component(ui.TextDisplay(
        "**Backend**\n"
        f"Python version: {python_version}\n"
        f"Discord library: {md.hyperlink('disnake', disnake_url)} {disnake_version}\n"
        f"Lines of code: {_bot_info.app_sloc}"
    ))  # fmt: skip
    bytes_, prefix = as_binary_unit(get_ram_usage())
    add_component(ui.TextDisplay(
        "**Performance**\n"
        f"Started: {md.format_dt(BOT_PROCESS.create_time(), 'R')}\n"
        f"Latency: {round(bot.latency * 1000)}ms\n"
        f"RAM usage: {bytes_}{prefix}B"
    ))  # fmt: skip

    if _bot_info.bot_public:
        builder.add_component(ui.ActionRow(ui.UrlButton(
            url=oauth_url(bot.user.id, scopes=("bot", "applications.commands")),
            label="Invite me!",
            emoji=EMOJIS.item_slot_drone.to_partial(),
        )))  # fmt: skip

    if __debug__:
        debug_components(builder)

    await builder.send_response(inter, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
