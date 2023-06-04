from __future__ import annotations

import importlib.util
import logging
import os
import typing as t
from collections import Counter
from datetime import datetime

from disnake.ext import commands
from disnake.utils import MISSING

from library_extensions import command_mention, walk_modules

if t.TYPE_CHECKING:
    import asyncio

    import aiohttp
    from disnake import (
        AllowedMentions,
        BaseActivity,
        CommandInteraction,
        GatewayParams,
        Intents,
        LocalizationProtocol,
        MemberCacheFlags,
        Status,
    )
    from typing_extensions import Unpack


LOGGER = logging.getLogger("bot")


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
    started_at: datetime
    command_invocations: Counter[str]
    _client: t.Any

    def __init__(self, *, client: t.Any, **kwargs: Unpack[BotParams]) -> None:
        super().__init__(**kwargs)
        self._client = client
        self.started_at = MISSING
        self.command_invocations = Counter()

    async def on_application_command(self, interaction: CommandInteraction) -> None:
        await super().on_application_command(interaction)
        command_name = interaction.application_command.name
        api_command = self.get_global_command_named(command_name)

        if api_command is None:
            LOGGER.warning(f"API command not found for {command_name!r}")
        else:
            self.command_invocations[command_mention(api_command)] += 1

    async def on_ready(self) -> None:
        LOGGER.info(f"{self.user.name} is online")

        if __debug__:
            limit = self.session_start_limit
            assert limit is not None
            LOGGER.info(
                f"Session start limit: total={limit.total}, remaining={limit.remaining}"
                f", reset={limit.reset_time:%d.%m.%Y %H:%M:%S}"
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
