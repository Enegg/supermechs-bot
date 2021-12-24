from __future__ import annotations

import logging
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from functools import cached_property, partial
from typing import Any, Final, Literal

import aiohttp
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

from config import HOME_GUILD_ID, LOGS_CHANNEL, OWNER_ID, TEST_GUILDS
from discotools import ChannelHandler, DiscordFormatter

parser = ArgumentParser()
parser.add_argument('--local', action='store_true')
parser.add_argument('--log-file', action='store_true')
args = parser.parse_args()
LOCAL: Final[bool] = args.local

logger = logging.getLogger('channel_logs')
logger.level = logging.INFO

load_dotenv()
TOKEN = os.environ.get('TOKEN_DEV' if LOCAL else 'TOKEN')

if TOKEN is None:
    raise EnvironmentError('TOKEN not found in environment variables')

# ------------------------------------------ Bot init ------------------------------------------

class HostedBot(commands.InteractionBot):
    def __init__(self, hosted: bool=False, **options: Any):
        options.setdefault('sync_permissions', True)
        super().__init__(**options)
        self.hosted = hosted
        self.run_time = datetime.now()


    async def on_slash_command_error(
        self,
        inter: disnake.ApplicationCommandInteraction,
        error: commands.CommandError
    ) -> None:
        if isinstance(error, (commands.UserInputError, commands.CheckFailure)):
            if isinstance(error, commands.NotOwner):
                msg = 'You cannot use this command.'

            else:
                msg = str(error)

            await inter.send(msg, ephemeral=True)
            return

        # tell the user there was an internal error
        if isinstance(error, commands.CommandInvokeError):
            origin = error.original

            if isinstance(origin, disnake.HTTPException) and origin.code == 50035:  # Invalid Form Body
                await inter.send('Message exceeded character limit...', ephemeral=True)

            else:
                await inter.send('Command executed with an error...', ephemeral=True)

        text = (f'{error}'
                f'\nCommand: `{inter.application_command.qualified_name}`'
                f"\nArguments: {', '.join(f'`{option}`: `{value}`' for option, value in inter.filled_options.items()) or 'None'}"
                f'\nPlace: {inter.guild or inter.channel}')

        logger.exception(text, exc_info=error)


    async def on_ready(self) -> None:
        text = f'{bot.user.name} is online'
        print(text, '-' * len(text), sep='\n')


    @cached_property
    def session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=self.http.connector)
        session._request = partial(session._request, proxy=self.http.proxy)
        return session


bot = HostedBot(
    hosted=LOCAL,
    owner_id=OWNER_ID,
    intents=disnake.Intents(guilds=True),
    activity=disnake.Game('under maintenance' if LOCAL else 'SuperMechs'),
    guild_ids=TEST_GUILDS if LOCAL else None)

# ----------------------------------------------------------------------------------------------

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
        action: Literal['load', 'reload', 'unload'] = 'reload',
        ext: str=None
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
                await inter.send('No extension cached.')
                return

            ext = self.last_ext

        funcs = {
            'load':   bot.load_extension,
            'reload': bot.reload_extension,
            'unload': bot.unload_extension}

        try:
            funcs[action](ext)

        except commands.ExtensionError as error:
            error_block = DiscordFormatter.formatException((type(error), error, error.__traceback__))
            await inter.send(f'An error occured:\n{error_block}', ephemeral=True)

        else:
            await inter.send('Success', ephemeral=True)

            self.last_ext = ext


    @extensions.autocomplete('ext')
    async def ext_autocomp(self, inter: disnake.MessageCommandInteraction, input: str) -> list[str]:
        input = input.lower()
        return [ext for ext in inter.bot.extensions if input in ext.lower()]


    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=[HOME_GUILD_ID])
    async def shutdown(self, inter: disnake.MessageCommandInteraction) -> None:
        """Terminates the bot connection."""
        await inter.send('I will be back', ephemeral=True)
        await bot.close()


class Misc(commands.Cog):
    @commands.slash_command()
    async def ping(self, inter: disnake.MessageCommandInteraction) -> None:
        """Shows bot latency"""
        await inter.send(f'Pong! {round(inter.bot.latency * 1000)}ms')


    @commands.slash_command()
    async def invite(self, inter: disnake.MessageCommandInteraction) -> None:
        """Sends an invite link for this bot to the channel"""
        await inter.send(disnake.utils.oauth_url(inter.bot.user.id, scopes=('bot', 'applications.commands')))


    @commands.slash_command(name='self')
    async def self_info(self, inter: disnake.MessageCommandInteraction) -> None:
        """Displays information about the bot."""
        app = await bot.application_info()
        invite = disnake.utils.oauth_url(bot.user.id, scopes=('bot', 'applications.commands'))
        desc = (
            f'Member of {len(bot.guilds)} server{"s" * (len(bot.guilds) != 1)}'
            f'\n**Author:** {app.owner.mention}'
            f'\n[**Invite link**]({invite})')

        uptime = datetime.now() - bot.run_time
        ss = uptime.seconds
        mm, ss = divmod(ss, 60)
        hh, mm = divmod(mm, 60)

        time_data: list[str] = []
        if uptime.days:
            time_data.append(f'{uptime.days} day{"s" * (uptime.days != 1)}')

        if hh:
            time_data.append(f'{hh} hour{"s" * (hh != 1)}')

        if mm:
            time_data.append(f'{mm} minute{"s" * (mm != 1)}')

        if ss:
            time_data.append(f'{ss} second{"s" * (ss != 1)}')

        embed = disnake.Embed(title='Bot info', description=desc, color=inter.me.color)

        tech_field = (
            f'Python build: {".".join(map(str, sys.version_info[:3]))} {sys.version_info.releaselevel}'
            f'\ndisnake version: {disnake.__version__}'
            f'\nUptime: {" ".join(time_data)}'
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name='Technical', value=tech_field)
        embed.set_footer(text='Created')
        embed.timestamp = bot.user.created_at

        await inter.send(embed=embed, ephemeral=True)

bot.add_cog(Setup())
bot.add_cog(Misc())
bot.load_extension('SM')

bot.run(TOKEN)
