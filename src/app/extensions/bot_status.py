import random
import types
from functools import partial
from typing import NamedTuple, Protocol

import disnake
from app.disnake_types import CommandInteraction
from discord import markdown as md
from discord.null_objects import NullUser
from disnake import Embed
from disnake.ext import tasks
from disnake.utils import oauth_url

from app import meta, state
from app.assets import ASSETS
from app.async_utils import gather
from app.bridges.telemetry import command_tracker
from app.core import CONFIG
from app.plugins_factory import create_plugin
from app.system import get_ram_usage, get_sloc
from app.utils import as_binary_unit

import supermechs

plugin = create_plugin(__name__)


class MiniAppInfo(Protocol):
    @property
    def owner(self) -> disnake.abc.User: ...
    @property
    def bot_public(self) -> bool: ...


class _State(NamedTuple):
    app_info: MiniAppInfo = types.SimpleNamespace(owner=NullUser(), bot_public=False)  # pyright: ignore[reportAssignmentType]
    app_sloc: int = 0
    lib_sloc: int = 0


_state: _State = _State()


@plugin.register_loop(wait_until_ready=True)
@tasks.loop(count=1)
async def load_state() -> None:
    global _state
    match supermechs.__path__:
        case [str() as path]:
            pass

        case unknown:
            msg = f"Expected a sequence of 1 path, got {unknown!r}"
            raise RuntimeError(msg)

    _state = _State._make(
        await gather(
            plugin.bot.application_info,
            partial(get_sloc, "src"),
            partial(get_sloc, path),
        )
    )


@plugin.slash_command()
async def frantic(inter: CommandInteraction) -> None:
    """Humiliate frantic users."""
    choice = random.choice(ASSETS.gifs["frantics"])
    await inter.response.send_message(choice)


@plugin.slash_command()
async def info(inter: CommandInteraction) -> None:
    """Display information about the bot."""
    bot = plugin.bot

    general_fields = [
        f"Developer: {_state.app_info.owner.mention}",
        f"Created: {md.format_dt(bot.user.created_at, 'R')}",
        f"Servers: {len(bot.guilds)}",
        f"Invoked commands: {command_tracker.total_invocations()}",
    ]
    if _state.app_info.bot_public:
        invite = oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
        general_fields.append(md.hyperlink("**Invite link**", invite))

    backend_fields = [
        f"Python version: {meta.python_version}",
        f"Discord library: {md.hyperlink('disnake', meta.disnake_url)} {meta.disnake_version}",
    ]
    backend_fields.append(f"Lines of code: {_state.app_sloc} bot + {_state.lib_sloc} SM library")

    supermechs_fields = [
        f"Registered players: {len(state.players.mapping)}",
        f"Default item pack: {md.hyperlink(state.item_pack.key, CONFIG.default_pack_url)}",
        f"Total items: {len(state.item_pack.items)}",
    ]
    bytes_, prefix = as_binary_unit(get_ram_usage())
    perf_fields = [
        f"Started: {md.format_dt(meta.started_at, 'R')}",
        f"Latency: {round(bot.latency * 1000)}ms",
        f"RAM usage: {bytes_}{prefix}B",
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


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def activity(inter: CommandInteraction) -> None:
    """Display command invocation activity."""
    desc = (
        "\n".join(
            f"{md.command_mention(command)}: {command.total_invocations}"
            for command in command_tracker.commands_data.values()
        )
        or "No invocations since bot started"
    )

    embed = Embed(title="Command activity", description=desc, timestamp=meta.started_at)
    await inter.response.send_message(embed=embed)


setup, teardown = plugin.create_extension_handlers()
