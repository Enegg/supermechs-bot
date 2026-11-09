import asyncio
from collections import abc
from functools import partial
from typing import Final, cast as type_cast, override

import psutil

import disnake
from disnake import Locale, LocalizationProtocol
from disnake.abc import Messageable
from disnake.ext import commands

from app.aio import HTTPSession
from app.core import CONFIG
from app.structs import BotUserInfo, ItemPack, LocaleInfo, LocalePair, SpritePack


# TODO: is there a better way to create objects that depend on a loop instance?
class MockEventLoop(asyncio.AbstractEventLoop):
    @override
    def set_debug(self, enabled: bool) -> None: ...
    @override
    def get_debug(self) -> bool:
        return False


DEFAULT_LOOP: Final[asyncio.AbstractEventLoop] = MockEventLoop()
APP_PROCESS: Final = psutil.Process()

# ----------------------------------------- set-once state -----------------------------------------
event_loop: asyncio.AbstractEventLoop = DEFAULT_LOOP
http_session: HTTPSession = ...  # pyright: ignore[reportAssignmentType]
"""App-lifetime HTTP session."""
logs_channel: Messageable | None = None
bot_user_info: BotUserInfo = BotUserInfo()

item_pack: ItemPack = ItemPack()
sprite_pack: SpritePack = {}

FALLBACK_LOCALE: Final = Locale.en_US
locale_info: Final[abc.MutableMapping[Locale, LocaleInfo]] = {}
i18n_stats: Final[abc.MutableMapping[LocalePair[str], str]] = {}
i18n_messages: Final[abc.MutableMapping[LocalePair[str], str]] = {}
i18n_command_locale: Final[abc.MutableMapping[str, dict[str, str]]] = {}
# provider only needs .get(_: str, /) -> Mapping[str, str] | None
localization_provider: Final[LocalizationProtocol] = type_cast(
    "LocalizationProtocol", i18n_command_locale
)

# ----------------------------------------- variable state -----------------------------------------
debug_log_components: bool = False
debug_reloaded_plugin_name: str | None = None
debug_locale_override: Locale | None = None

app_sloc: int = 0
command_mentions: Final[abc.MutableMapping[str, str]] = {}

# this is checked in Client.__init__
disnake.VoiceClient.warn_nacl = False
BOT: Final = commands.InteractionBot(
    # NOTE: guilds provides things like Interaction.me,
    # which is typed as -> Member | ClientUser, but can actually be None
    intents=disnake.Intents(guilds=True),
    activity=disnake.Game("SuperMechs"),
    allowed_mentions=disnake.AllowedMentions.none(),
    localization_provider=localization_provider,
    test_guilds=CONFIG.test_guild_ids if CONFIG.indev else None,
    command_sync_flags=commands.CommandSyncFlags(
        sync_commands_debug=CONFIG.debug_command_sync,
        sync_on_cog_actions=False,
    ),
    loop=DEFAULT_LOOP,
)
if CONFIG.indev:
    BOT.get_global_command_named = partial(BOT.get_guild_command_named, CONFIG.dev_guild_id)

# this patch has to be done mostly because plugins call this method with no opt-out
BOT._schedule_delayed_command_sync = lambda: None  # pyright: ignore[reportPrivateUsage]
