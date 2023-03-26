from __future__ import annotations

import importlib.util
import logging
import os
import typing as t
from datetime import datetime

from disnake import CommandInteraction
from disnake.ext import commands
from disnake.utils import MISSING

from library_extensions import localized_text, walk_modules

if t.TYPE_CHECKING:
    import asyncio

    import aiohttp
    from disnake import (
        AllowedMentions,
        BaseActivity,
        GatewayParams,
        Intents,
        LocalizationProtocol,
        MemberCacheFlags,
        Status,
    )


LOGGER = logging.getLogger(__name__)


class BotParams(t.TypedDict, total=False):
    owner_id: int | None
    owner_ids: set[int] | None
    reload: bool
    sync_commands: bool
    sync_commands_debug: bool
    sync_commands_on_cog_unload: bool
    test_guilds: t.Sequence[int] | None
    asyncio_debug: bool
    loop: asyncio.AbstractEventLoop | None
    shard_id: int | None
    shard_count: int | None
    enable_debug_events: bool
    enable_gateway_error_handler: bool
    gateway_params: GatewayParams | None
    connector: aiohttp.BaseConnector | None
    proxy: str | None
    proxy_auth: aiohttp.BasicAuth | None
    assume_unsync_clock: bool
    max_messages: int | None
    application_id: int | None
    heartbeat_timeout: float
    guild_ready_timeout: float
    allowed_mentions: AllowedMentions | None
    activity: BaseActivity | None
    status: Status | str | None
    intents: Intents | None
    chunk_guilds_at_startup: bool | None
    member_cache_flags: MemberCacheFlags | None
    localization_provider: LocalizationProtocol | None
    strict_localization: bool


class ModularBot(commands.InteractionBot):
    started_at: datetime = MISSING

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

    async def on_ready(self) -> None:
        LOGGER.info(f"{self.user.name} is online")

        if __debug__:
            limit = self.session_start_limit
            assert limit is not None
            LOGGER.info(
                f"Session start limit: {limit.total=}, {limit.remaining=}"
                f", {limit.reset_time=:%d.%m.%Y %H:%M:%S}"
            )

    async def login(self, token: str) -> None:
        LOGGER.info("Starting...")
        self.started_at = datetime.now()
        await super().login(token)

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
