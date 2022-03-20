from __future__ import annotations

import io
import logging
import os
import sys
import traceback
from argparse import ArgumentParser
from datetime import datetime
from functools import cached_property, partial
from typing import Any, Final, Literal, Optional

import aiohttp
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

from config import HOME_GUILD_ID, LOGS_CHANNEL, OWNER_ID, TEST_GUILDS
from discotools import ChannelHandler, FileRecord, str_to_file

parser = ArgumentParser()
parser.add_argument("--local", action="store_true")
parser.add_argument("--db_enabled", action="store_true")
parser.add_argument("--log-file", action="store_true")
args = parser.parse_args()
LOCAL: Final[bool] = args.local
DB_FEATURES: bool = args.db_enabled

logging.setLogRecordFactory(FileRecord)
logger = logging.getLogger("channel_logs")
logger.level = logging.INFO

load_dotenv()
TOKEN = os.environ.get("TOKEN_DEV" if LOCAL else "TOKEN")

if TOKEN is None:
    raise EnvironmentError("TOKEN not found in environment variables")

if DB_FEATURES:
    DB_TOKEN = os.environ.get("DB_TOKEN")

    if DB_TOKEN is None:
        raise EnvironmentError("DB_TOKEN not found in environment variables")

    import certifi
    from motor.motor_asyncio import AsyncIOMotorClient
    from odmantic import AIOEngine
    from pymongo.errors import PyMongoError

    if LOCAL:
        engine = AIOEngine()

    else:
        engine = AIOEngine(AsyncIOMotorClient(
            DB_TOKEN,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where()
        ))

else:
    engine = None

# ------------------------------------------ Bot init ------------------------------------------

class SMBot(commands.InteractionBot):
    def __init__(
        self, hosted: bool = False, engine: AIOEngine | None = None, **options: Any
    ) -> None:
        options.setdefault("sync_permissions", True)
        super().__init__(**options)
        self.hosted = hosted
        self.run_time = datetime.now()

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
                    f'`{option}`: `{value}`'
                    for option, value
                    in inter.filled_options.items()
                ) or 'None'

                text = (
                    f"{error}"
                    f"\nUser: {inter.author.mention} ({inter.author.display_name})"
                    f"\nCommand: `{inter.application_command.qualified_name}`"
                    f"\nArguments: {arguments}"
                    f"\nPlace: {inter.guild or inter.channel}")

                logger.exception(text, exc_info=error)
                await inter.send(
                    "Command executed with an error...",
                    allowed_mentions=disnake.AllowedMentions.none(),
                    ephemeral=True)

    async def on_ready(self) -> None:
        text = f"{bot.user.name} is online"
        print(text, "-" * len(text), sep="\n")

    @cached_property
    def session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=self.http.connector)
        session._request = partial(session._request, proxy=self.http.proxy)
        return session


bot = SMBot(
    hosted=LOCAL,
    engine = engine,
    owner_id=OWNER_ID,
    intents=disnake.Intents(guilds=True),
    activity=disnake.Game("under maintenance" if LOCAL else "SuperMechs"),
    guild_ids=TEST_GUILDS if LOCAL else None)

# ------------------------------------------------------------------------------------------------

handler = ChannelHandler(LOGS_CHANNEL, bot, level=logging.INFO)
logger.addHandler(handler)


class Setup(commands.Cog):
    """Module management commands for development purposes."""

    def __init__(self):
        self.last_ext = None

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=TEST_GUILDS)
    async def extensions(
        self,
        inter: disnake.MessageCommandInteraction,
        action: Literal["load", "reload", "unload"] = "reload",
        ext: Optional[str] = None
    ) -> None:
        """Extension manager

        Parameters
        -----------
        action:
            The type of action to perform
        ext:
            The name of extension to perform action on"""
        if ext is None:
            if self.last_ext is None:
                await inter.send("No extension cached.")
                return

            ext = self.last_ext

        funcs = {
            "load":   bot.load_extension,
            "reload": bot.reload_extension,
            "unload": bot.unload_extension}

        try:
            funcs[action](ext)

        except commands.ExtensionError as error:
            with io.StringIO() as sio:
                sio.write("```py\n")
                traceback.print_exception(type(error), error, error.__traceback__, file=sio)
                sio.write("```")
                error_block = sio.getvalue()
            await inter.send(f"An error occured:\n{error_block}", ephemeral=True)

        else:
            await inter.send("Success", ephemeral=True)

            self.last_ext = ext

    @extensions.autocomplete("ext")
    async def ext_autocomp(self, inter: disnake.MessageCommandInteraction, input: str) -> list[str]:
        input = input.lower()
        return [ext for ext in inter.bot.extensions if input in ext.lower()]

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=[HOME_GUILD_ID])
    async def shutdown(self, inter: disnake.MessageCommandInteraction) -> None:
        """Terminates the bot connection."""
        await inter.send("I will be back", ephemeral=True)
        await bot.close()

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(name="raise", default_permission=False, guild_ids=[HOME_GUILD_ID])
    async def force_error(self, inter: disnake.MessageCommandInteraction, exception: str, arguments: Optional[str] = None) -> None:
        """Explicitly raises provided exception

        Parameters
        -----------
        exception:
            Name of the exception to raise
        arguments:
            Optional arguments to pass to the exception"""
        err: type[commands.CommandError] | None = getattr(commands.errors, exception, None)

        if err is None or not issubclass(err, commands.CommandError):
            raise commands.UserInputError("Exception specified has not been found.")

        try:
            raise err(arguments)

        finally:
            await inter.send("Success", ephemeral=True)

    @force_error.autocomplete("exception")
    async def raise_autocomp(self, inter: disnake.MessageCommandInteraction, input: str) -> list[str]:
        if len(input) < 2:
            return ["Start typing to get options..."]

        input = input.lower()
        return [exc for exc in commands.errors.__all__ if input in exc.lower()][:25]

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=TEST_GUILDS)
    async def database(self, inter: disnake.MessageCommandInteraction) -> None:
        """Show info about the database"""
        await inter.response.defer()

        assert bot.engine is not None

        try:
            data = await bot.engine.client.server_info()

        except PyMongoError:
            await inter.send("Unable to connect.")
            raise

        data = str(data)

        if len(data) > 2000:
            await inter.send(file=str_to_file(data))

        else:
            await inter.send(data)


class Misc(commands.Cog):
    @commands.slash_command()
    async def ping(self, inter: disnake.MessageCommandInteraction) -> None:
        """Shows bot latency"""
        await inter.send(f'Pong! {round(inter.bot.latency * 1000)}ms')

    @commands.slash_command()
    async def invite(self, inter: disnake.MessageCommandInteraction) -> None:
        """Sends an invite link for this bot to the channel"""
        await inter.send(
            disnake.utils.oauth_url(inter.bot.user.id, scopes=("bot", "applications.commands"))
        )

    @commands.slash_command(name="self")
    async def self_info(self, inter: disnake.MessageCommandInteraction) -> None:
        """Displays information about the bot."""
        app = await bot.application_info()
        desc = (
            f'Member of {len(bot.guilds)} server{"s" * (len(bot.guilds) != 1)}'
            f"\n**Author:** {app.owner.mention}")

        if app.bot_public:
            invite = disnake.utils.oauth_url(bot.user.id, scopes=("bot", "applications.commands"))
            desc += f"\n[**Invite link**]({invite})"

        uptime = datetime.now() - bot.run_time
        ss = uptime.seconds
        mm, ss = divmod(ss, 60)
        hh, mm = divmod(mm, 60)

        time_data: list[str] = []
        if uptime.days != 0:
            time_data.append(f'{uptime.days} day{"s" * (uptime.days != 1)}')

        if hh != 0:
            time_data.append(f"{hh}h")

        if mm != 0:
            time_data.append(f"{mm}min")

        if ss != 0:
            time_data.append(f"{ss}s")

        tech_field = (
            f"Python build: {'.'.join(map(str, sys.version_info[:3]))} {sys.version_info.releaselevel}"
            f"\ndisnake version: {disnake.__version__}"
            f"\nUptime: {' '.join(time_data)}"
        )

        embed = (
            disnake.Embed(title="Bot info", description=desc, color=inter.me.color)
            .set_thumbnail(url=bot.user.display_avatar.url)
            .add_field(name="Technical", value=tech_field)
            .set_footer(text="Created")
            )
        embed.timestamp = bot.user.created_at

        await inter.send(embed=embed, ephemeral=True)


bot.add_cog(Setup())
bot.add_cog(Misc())
bot.load_extension("SM")

bot.run(TOKEN)
