from __future__ import annotations

import importlib.util
import logging
import os
import typing as t
from datetime import datetime
from functools import partial

from disnake import (
    AllowedMentions,
    BaseActivity,
    CommandInteraction,
    Intents,
    Interaction,
    Member,
    User,
)
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.utils import MISSING

from abstract.files import URL
from library_extensions import ChannelHandler, walk_modules
from shared import SESSION_CTX

from SuperMechs.pack_interface import PackInterface
from SuperMechs.player import Player
from SuperMechs.urls import PACK_V2_URL

LOGGER = logging.getLogger(__name__)


class SMBot(commands.InteractionBot):
    started_at: datetime
    players: dict[int, Player]
    default_pack: PackInterface
    dev_mode: bool

    def __init__(
        self,
        *,
        dev_mode: bool = False,
        logs_channel_id: int | None = None,
        owner_id: int | None = None,
        reload: bool = False,
        sync_commands: bool = True,
        sync_commands_debug: bool = False,
        sync_commands_on_cog_unload: bool = True,
        test_guilds: t.Sequence[int] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        activity: BaseActivity | None = None,
        intents: Intents | None = None,
        strict_localization: bool = False,
    ):
        super().__init__(
            owner_id=owner_id,
            reload=reload,
            sync_commands=sync_commands,
            sync_commands_debug=sync_commands_debug,
            sync_commands_on_cog_unload=sync_commands_on_cog_unload,
            test_guilds=test_guilds,
            allowed_mentions=allowed_mentions,
            activity=activity,
            intents=intents,
            strict_localization=strict_localization,
        )
        self.started_at = MISSING
        self.players = {}
        self.logs_channel = logs_channel_id
        self.default_pack = PackInterface()
        self.dev_mode = dev_mode

    async def on_slash_command_error(
        self, inter: CommandInteraction, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.NotOwner):
            info = "This is a developer-only command."

        elif isinstance(error, (commands.UserInputError, commands.CheckFailure)):
            info = str(error)

        elif isinstance(error, commands.MaxConcurrencyReached):
            if error.number == 1 and error.per is commands.BucketType.user:
                info = "Your previous invocation of this command has not finished executing."

            else:
                info = str(error)

        else:
            arguments = ", ".join(
                f"`{option}: {value}`" for option, value in inter.filled_options.items()
            )

            text = (
                f"{error}"
                f"\nPlace: `{inter.guild or inter.channel}`"
                f"\nCommand invocation: {inter.author.mention} ({inter.author.display_name})"
                f" `/{inter.application_command.qualified_name}` {arguments}"
            )

            if __debug__:
                info = text

            else:
                LOGGER.exception(text, exc_info=error)
                info = "Command executed with an error..."
        await inter.send(info, ephemeral=True)

    async def login(self, token: str) -> None:
        LOGGER.info("Starting...")
        self.started_at = datetime.now()
        await super().login(token)

    async def before_connect(self) -> None:
        try:
            await self.default_pack.load(URL(PACK_V2_URL))

        except Exception as err:
            LOGGER.warning("Failed to load items: ", exc_info=err)

    async def on_ready(self) -> None:
        LOGGER.info(f"{self.user.name} is online")

        if __debug__:
            limit = self.session_start_limit
            assert limit is not None
            LOGGER.info(
                f"Session start limit: {limit.total=}, {limit.remaining=}, {limit.reset_time=:%d.%m.%Y %H:%M:%S}"
            )

    async def setup_channel_logger(self, channel_id: int) -> None:
        channel = await self.fetch_channel(channel_id)

        if not isinstance(channel, Messageable):
            raise TypeError("Channel is not Messageable")

        LOGGER.addHandler(ChannelHandler(channel, logging.WARNING))
        LOGGER.info("Warnings & errors redirected to logs channel")

    def create_aiohttp_session(self) -> None:
        from aiohttp import ClientSession, ClientTimeout

        session = ClientSession(connector=self.http.connector, timeout=ClientTimeout(total=30))
        session._request = partial(session._request, proxy=self.http.proxy)
        SESSION_CTX.set(session)

    async def close_aiohttp_session(self) -> None:
        session = SESSION_CTX.get(None)

        if session is not None:
            await session.close()

    async def close(self) -> None:
        await self.close_aiohttp_session()
        await super().close()

    def load_extensions(
        self,
        root_module: str,
        *,
        package: str | None = None,
        ignore: t.Iterable[str] | t.Callable[[str], bool] | None = None,
    ) -> None:
        if "/" in root_module or "\\" in root_module:
            path = os.path.relpath(root_module)
            if ".." in path:
                raise ValueError(
                    "Paths outside the cwd are not supported. Try using the module name instead."
                )
            root_module = path.replace(os.sep, ".")

        root_module = self._resolve_name(root_module, package)

        if (spec := importlib.util.find_spec(root_module)) is None:
            raise commands.ExtensionError(
                f"Unable to find root module '{root_module}'", name=root_module
            )

        if (paths := spec.submodule_search_locations) is None:
            raise commands.ExtensionError(
                f"Module '{root_module}' is not a package", name=root_module
            )
        for module_name in walk_modules(paths, f"{spec.name}.", ignore):
            self.load_extension(module_name)

    def get_player(self, data: User | Member | Interaction, /) -> Player:
        """Return a Player object from object containing user ID."""
        match data:
            case User(id=id, name=name) | Member(id=id, name=name):
                pass

            case Interaction(author=author):
                id = author.id
                name = author.name

            case _:
                raise TypeError(f"Invalid type: {type(data)}")

        if id not in self.players:
            LOGGER.info(f"New player created: {id} ({name})")
            self.players[id] = Player(id=id, name=name)

        return self.players[id]


# due to disnake bug this cannot be Bot method
@commands.register_injection
def player_injector(inter: CommandInteraction) -> Player:
    assert isinstance(inter.bot, SMBot)
    return inter.bot.get_player(inter)
