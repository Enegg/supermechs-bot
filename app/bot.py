from __future__ import annotations

import importlib.util
import logging
import os
import typing as t
from datetime import datetime
from functools import partial

from disnake import CommandInteraction
from disnake.abc import Messageable
from disnake.ext import commands
from disnake.utils import MISSING

from abstract.files import URL
from library_extensions import ChannelHandler, localized_text, walk_modules
from shared import SESSION_CTX

from SuperMechs.pack_interface import PackInterface
from SuperMechs.urls import PACK_V2_URL

LOGGER = logging.getLogger(__name__)


class SMBot(commands.InteractionBot):
    started_at: datetime
    default_pack: PackInterface

    if not t.TYPE_CHECKING:
        # this is to avoid retyping all of the kwargs
        def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
            super().__init__(*args, **kwargs)
            self.started_at = MISSING
            self.default_pack = PackInterface()

    async def on_slash_command_error(
        self, inter: CommandInteraction, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.NotOwner):
            info = localized_text(
                "This is a developer-only command.", "CMD_DEV", self.i18n, inter.locale
            )

        elif isinstance(error, (commands.UserInputError, commands.CheckFailure)):
            info = str(error)

        elif isinstance(error, commands.MaxConcurrencyReached):
            if error.number == 1 and error.per is commands.BucketType.user:
                info = localized_text(
                    "Your previous invocation of this command has not finished executing.",
                    "CMD_RUNNING",
                    self.i18n,
                    inter.locale,
                )

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

                info = localized_text(
                    "Command executed with an error...", "CMD_ERROR", self.i18n, inter.locale
                )

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
                f"Session start limit: {limit.total=}, {limit.remaining=}"
                f", {limit.reset_time=:%d.%m.%Y %H:%M:%S}"
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
