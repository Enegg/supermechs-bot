import random
import sys
from typing import Final

import anyio

from discord import markdown as md
from disnake import __version__ as disnake_version
from disnake.utils import oauth_url

from app import init, ui
from app.assets import ASSETS, EMOJIS
from app.core import CONFIG, state
from app.devtools import debug_components
from app.plugins_factory import create_plugin
from app.typeshed import CommandInteraction
from app.utils import as_binary_unit
from resources import HttpResource

plugin = create_plugin(__name__)

python_version: Final = ".".join(map(str, sys.version_info[:3]))
disnake_url: Final = "https://github.com/DisnakeDev/disnake"


@plugin.load_hook(post=True)
async def _() -> None:
    async with anyio.create_task_group() as tg:
        tg.start_soon(init.init_app_info)
        tg.start_soon(init.init_sloc)


@plugin.slash_command(name="frantic")
async def slash_frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.frantic_gifs)
    await inter.response.send_message(choice)


@plugin.slash_command(name="info")
async def slash_info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    components: ui.MessageComponents = []
    container, add_component = ui.container(accent_color=inter.me.color)
    components.append(container)

    if (team := state.bot_user_info.team) is not None:
        # when an app is team-owned, .owner is a pseudo-user that represents the team
        # and doesn't really have any useful attributes
        assert team.owner_id is not None  # TODO: disnake#1630
        developer_line = f"Developer: {md.user_mention(team.owner_id)}"
        if len(team.members) > 1:
            if len(team.members) == 2:  # noqa: PLR2004
                developer_line += " and 1 other"
            else:
                developer_line += f" and {len(team.members)} others"
    else:
        developer_line = f"Developer: {state.bot_user_info.owner.mention}"

    add_component(ui.Section(
        ui.TextDisplay(
            "## Bot info\n"
            "**General**\n"
            f"{developer_line}\n"
            f"Created: {md.format_dt(state.BOT.user.created_at, 'R')}\n"
            f"Servers: {len(state.BOT.guilds)}"
        ),
        accessory=ui.thumbnail(inter.me.display_avatar),
    ))  # fmt: skip

    pack_key = "Built-in items pack"

    if isinstance(CONFIG.item_pack_uri, HttpResource):
        pack_key = md.hyperlink(pack_key, CONFIG.item_pack_uri.uri)

    item_pack = state.item_pack
    add_component(ui.TextDisplay(
        "**SuperMechs**\n"
        f"Item pack: {pack_key}\n"
        f"Total items: {len(item_pack.reloaded_items)} reloaded, {len(item_pack.legacy_items)} legacy"
    ))  # fmt: skip
    add_component(ui.TextDisplay(
        "**Backend**\n"
        f"Python version: {python_version}\n"
        f"Discord library: {md.hyperlink('disnake', disnake_url)} {disnake_version}\n"
        f"Lines of code: {state.app_sloc}"
    ))  # fmt: skip
    bytes_, prefix = as_binary_unit(state.APP_PROCESS.memory_info().rss)
    add_component(ui.TextDisplay(
        "**Performance**\n"
        f"Started: {md.format_dt(state.APP_PROCESS.create_time(), 'R')}\n"
        f"Latency: {round(state.BOT.latency * 1000)}ms\n"
        f"RAM usage: {bytes_}{prefix}B"
    ))  # fmt: skip

    if state.bot_user_info.bot_public:
        components.append(ui.ActionRow(ui.UrlButton(
            url=oauth_url(state.BOT.user.id, scopes=("bot", "applications.commands")),
            label="Invite me!",
            emoji=EMOJIS.item_slot_drone.to_partial(),
        )))  # fmt: skip

    if __debug__:
        debug_components(components)

    await inter.response.send_message(components=components, ephemeral=True)


setup, teardown = plugin.create_extension_handlers()
