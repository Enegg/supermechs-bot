from __future__ import annotations

import logging
import typing as t
from datetime import datetime
from functools import cached_property, partial
from json import JSONDecodeError

import aiohttp
from disnake import CommandInteraction, Interaction, Member, User
from disnake.abc import Messageable
from disnake.ext import commands

from config import DEFAULT_PACK_URL
from lib_helpers import ChannelHandler
from lib_helpers import CommandInteraction as SMCommandInteraction
from SuperMechs.core import abbreviate_names
from SuperMechs.item import AnyItem, Item
from SuperMechs.player import Player
from SuperMechs.types import ItemPack, PackConfig
from utils import MISSING

logger = logging.getLogger(f"main.{__name__}")


class SMBot(commands.InteractionBot):
    items_cache: dict[str, AnyItem]
    item_abbrevs: dict[str, set[str]]
    item_pack: PackConfig

    def __init__(
        self, test_mode: bool = False, logs_channel_id: int | None = None, **options: t.Any
    ) -> None:
        super().__init__(**options)
        self.test_mode = test_mode
        self.run_time: datetime = MISSING
        self.players: dict[int, Player] = {}
        self.logs_channel = logs_channel_id

    async def on_slash_command_error(
        self, inter: CommandInteraction, error: commands.CommandError
    ) -> None:
        match error:
            case commands.NotOwner():
                await inter.send("This is a developer-only command.", ephemeral=True)

            case commands.UserInputError() | commands.CheckFailure():
                await inter.send(str(error), ephemeral=True)

            case commands.MaxConcurrencyReached(number=1, per=commands.BucketType.user):
                text = "Your previous invocation of this command has not finished executing."
                await inter.send(text, ephemeral=True)

            case commands.MaxConcurrencyReached():
                await inter.send(str(error), ephemeral=True)

            case _:
                arguments = ", ".join(
                    f"`{option}: {value}`" for option, value in inter.filled_options.items()
                )

                text = (
                    f"{error}"
                    f"\nPlace: `{inter.guild or inter.channel}`"
                    f"\nCommand invocation: {inter.author.mention} ({inter.author.display_name})"
                    f" `/{inter.application_command.qualified_name}` {arguments}"
                )

                logger.exception(text, exc_info=error)
                await inter.send("Command executed with an error...", ephemeral=True)

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.run_time = datetime.now()
        await self.login(token)

        if self.logs_channel is not None:
            channel = await self.fetch_channel(self.logs_channel)

            if not isinstance(channel, Messageable):
                raise TypeError("Channel is not Messageable")

            logger.addHandler(ChannelHandler(channel, logging.WARNING))
            logger.info("Warnings & errors redirected to logs channel")

        try:
            await self.load_item_pack(DEFAULT_PACK_URL)

        except (JSONDecodeError, aiohttp.ClientResponseError) as e:
            logger.warning("Error while fetching items: ", e)
            return

        self.item_abbrevs = abbreviate_names(self.items_cache)

        await self.connect(reconnect=reconnect)

    async def on_ready(self) -> None:
        logger.info(f"{self.user.name} is online")

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            connector=self.http.connector, timeout=aiohttp.ClientTimeout(total=30)
        )
        session._request = partial(session._request, proxy=self.http.proxy)
        return session

    async def load_item_pack(self, pack_url: str, /) -> None:
        """Loads an item pack from url and sets it as active pack."""
        logger.info("Fetching item pack")

        async with self.session.get(pack_url) as response:
            response.raise_for_status()
            pack: ItemPack = await response.json(encoding="utf-8", content_type=None)

        self.item_pack = pack["config"]
        self.items_cache = {
            item_dict["name"]: Item.from_json_v1(item_dict, pack=pack["config"])
            for item_dict in pack["items"]
        }
        logger.info(f"Item pack loaded: {self.item_pack['name']}")

    def get_player(self, data: User | Member | commands.Context | Interaction | int, /) -> Player:
        """Return a Player object from object containing user ID."""
        match data:
            case User() | Member():
                id = data.id

            case commands.Context() | Interaction():
                id = data.author.id

            case int():
                id = data

            case _:
                raise TypeError(f"Invalid type: {type(data)}")

        if id not in self.players:
            logger.info("New player created: %d", id)
            self.players[id] = Player(id=id)

        return self.players[id]


# due to disnake bug this cannot be Bot method
@commands.register_injection
def player_injector(inter: SMCommandInteraction) -> Player:
    return inter.bot.get_player(inter)
