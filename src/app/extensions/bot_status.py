import random
import sys
from functools import partial
from typing import Final

from discord import markdown as md
from disnake import __version__ as disnake_version
from disnake.utils import oauth_url

from app import ui
from app.assets import ASSETS, EMOJIS
from app.async_utils import gather
from app.core import CONFIG, AppState
from app.core.state import BotUserInfo
from app.devtools import debug_components
from app.plugins_factory import create_plugin
from app.typeshed import CommandInteraction
from app.utils import as_binary_unit, get_ram_usage, get_sloc
from resources import HttpResource

plugin = create_plugin(__name__)

python_version: Final = ".".join(map(str, sys.version_info[:3]))
disnake_url: Final = "https://github.com/DisnakeDev/disnake"


@plugin.load_hook(post=True)
async def load_info() -> None:
    app_info, app_sloc = await gather(
        AppState.bot.application_info,
        partial(get_sloc, "src"),
    )
    AppState.bot_user_info = BotUserInfo(
        owner=app_info.owner,
        bot_public=app_info.bot_public,
    )
    AppState.app_sloc = app_sloc


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.frantic_gifs)
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    components: ui.MessageComponents = []
    container, add_component = ui.container(accent_color=inter.me.color)
    components.append(container)
    add_component(ui.Section(
        ui.TextDisplay(
            "## Bot info\n"
            "**General**\n"
            f"Developer: {AppState.bot_user_info.owner.mention}\n"
            f"Created: {md.format_dt(AppState.bot.user.created_at, 'R')}\n"
            f"Servers: {len(AppState.bot.guilds)}"
        ),
        accessory=ui.thumbnail(inter.me.display_avatar),
    ))  # fmt: skip

    pack_key = "Built-in items pack"

    if isinstance(CONFIG.item_pack_uri, HttpResource):
        pack_key = md.hyperlink(pack_key, CONFIG.item_pack_uri.uri)

    item_pack = AppState.item_pack
    add_component(ui.TextDisplay(
        "**SuperMechs**\n"
        f"Item pack: {pack_key}\n"
        f"Total items: {len(item_pack.reloaded_items)} reloaded, {len(item_pack.legacy_items)} legacy"
    ))  # fmt: skip
    add_component(ui.TextDisplay(
        "**Backend**\n"
        f"Python version: {python_version}\n"
        f"Discord library: {md.hyperlink('disnake', disnake_url)} {disnake_version}\n"
        f"Lines of code: {AppState.app_sloc}"
    ))  # fmt: skip
    bytes_, prefix = as_binary_unit(get_ram_usage(AppState.app_process))
    add_component(ui.TextDisplay(
        "**Performance**\n"
        f"Started: {md.format_dt(AppState.app_process.create_time(), 'R')}\n"
        f"Latency: {round(AppState.bot.latency * 1000)}ms\n"
        f"RAM usage: {bytes_}{prefix}B"
    ))  # fmt: skip

    components: ui.MessageComponents = []
    components.append(container)

    if AppState.bot_user_info.bot_public:
        components.append(ui.ActionRow(ui.UrlButton(
            url=oauth_url(AppState.bot.user.id, scopes=("bot", "applications.commands")),
            label="Invite me!",
            emoji=EMOJIS.item_slot_drone.to_partial(),
        )))  # fmt: skip

    if __debug__:
        debug_components(components)

    await inter.response.send_message(components=components, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
