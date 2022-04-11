from __future__ import annotations

import logging
import typing as t
from datetime import datetime
from functools import cached_property, partial
from json import JSONDecodeError

import aiohttp
import disnake
from disnake.ext import commands

from config import DEFAULT_PACK_URL
from SuperMechs.item import AnyItem, Item
from SuperMechs.player import Player
from SuperMechs.types import ItemPack, PackConfig
from utils import MISSING, abbreviate_names

if t.TYPE_CHECKING:
    from odmantic import AIOEngine

logger = logging.getLogger("channel_logs")


class SMBot(commands.InteractionBot):
    items_cache: dict[str, AnyItem]
    item_abbrevs: dict[str, set[str]]
    item_pack: PackConfig

    def __init__(
        self, hosted: bool = False, engine: AIOEngine | None = None, **options: t.Any
    ) -> None:
        options.setdefault("sync_permissions", True)
        super().__init__(**options)
        self.hosted = hosted
        self.run_time = MISSING
        self.players: dict[int, Player] = {}

        self.engine = engine

    async def on_slash_command_error(
        self,
        inter: disnake.ApplicationCommandInteraction,
        error: commands.CommandError
    ) -> None:
        match error:
            case commands.NotOwner():
                await inter.send("This is a developer-only command.", ephemeral=True)

            case commands.UserInputError() | commands.CheckFailure():
                await inter.send(error, ephemeral=True)

            case commands.MaxConcurrencyReached():
                if error.per is commands.BucketType.user:
                    text = "Your previous invocation of this command has not finished executing."

                else:
                    text = str(error)

                await inter.send(text, ephemeral=True)

            case _:
                arguments = ', '.join(
                    f'`{option}: {value}`'
                    for option, value
                    in inter.filled_options.items()
                ) or 'None'

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

        try:
            await self.load_item_pack(DEFAULT_PACK_URL)

        except (JSONDecodeError, aiohttp.ClientResponseError) as e:
            logger.warning("Error while fetching items: ", e)
            return

        self.item_abbrevs = abbreviate_names(self.items_cache)

        await self.connect(reconnect=reconnect)

    async def on_ready(self) -> None:
        text = f"{self.user.name} is online"
        print(text, "-" * len(text), sep="\n")

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=self.http.connector)
        session._request = partial(session._request, proxy=self.http.proxy)
        return session

    async def load_item_pack(self, pack_url: str, /) -> None:
        """Loads an item pack from url and sets it as active pack."""
        async with self.session.get(pack_url) as response:
            response.raise_for_status()
            pack: ItemPack = await response.json(encoding="utf-8", content_type=None)

        self.item_pack = pack["config"]
        self.items_cache = {
            item_dict["name"]: Item(**item_dict, pack=pack["config"])  # type: ignore[assignment]
            for item_dict in pack["items"]}
        logger.info(f"Item pack loaded: {self.item_pack['name']}")

    def get_player(
        self, data: disnake.User | disnake.Member | commands.Context | disnake.Interaction | int, /
    ) -> Player:
        """Return a Player object from object containing user ID."""
        match data:
            case disnake.User() | disnake.Member():
                id = data.id

            case commands.Context() | disnake.Interaction():
                id = data.author.id

            case int():
                id = data

            case _:
                raise TypeError(f"Invalid type: {type(data)}")

        if id not in self.players:
            self.players[id] = Player(id=id)

        return self.players[id]
