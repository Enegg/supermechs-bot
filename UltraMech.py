from __future__ import annotations

import importlib
import os
import traceback
from argparse import ArgumentParser
from typing import *

import aiohttp
import disnake
from disnake.ext import commands
from disnake.ext.commands import errors
from dotenv import load_dotenv

from config import LOGS_CHANNEL, PREFIX_HOST, PREFIX_LOCAL

parser = ArgumentParser()
parser.add_argument('--local', action='store_true')
parser.add_argument('--prefix', type=str)
# parser.add_argument('--log-file', action='store_true')
args = parser.parse_args()
LOCAL: bool = args.local

load_dotenv()
TOKEN = os.environ.get('TOKEN')

if TOKEN is None:
    raise EnvironmentError('TOKEN not found in environment variables')


if args.prefix:
    PREFIX: str = args.prefix

elif LOCAL:
    PREFIX = PREFIX_LOCAL

else:
    PREFIX = PREFIX_HOST


def prefix_handler(bot: HostedBot, msg: disnake.Message) -> str | tuple[str, str]:
    if isinstance(msg.channel, disnake.DMChannel):
        return (PREFIX, '')

    return PREFIX


# ------------------------------------------ Bot init ------------------------------------------

simple_reactions: dict[type[commands.CommandError], str] = {
    errors.CommandNotFound: '❓',
    errors.CheckFailure: '🔒',
    errors.NotOwner: '🔒',
    errors.CommandOnCooldown: '🕓'}

class HostedBot(commands.Bot):
    def __init__(self, hosted: bool=False, **options: Any):
        super().__init__(**options)
        self.hosted = hosted
        self.session = aiohttp.ClientSession()


    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if type(error) in simple_reactions:
            await ctx.message.add_reaction(simple_reactions[type(error)])
            return

        if isinstance(error, errors.BadArgument):
            await ctx.send(str(error), delete_after=10.0)

        else:
            traceback.print_exception(type(error), error, None)

            if bot.hosted:
                channel = bot.get_channel(LOGS_CHANNEL)
                assert isinstance(channel, disnake.TextChannel)
                await channel.send(f'{error}\n{type(error)}')


    async def on_ready(self):
        text = f'{bot.user.name} is online'
        print(text, f'The prefix is {PREFIX}', '-' * len(text), sep='\n')


if LOCAL:
    activity = disnake.Game('under maintenance')

else:
    activity = disnake.Game('SuperMechs')


intents = disnake.Intents(guilds=True, members=True, emojis=True, messages=True, reactions=True)
bot = HostedBot(command_prefix=prefix_handler, hosted=LOCAL, intents=intents, activity=activity, test_guilds=[624937100034310164])

# ----------------------------------------------------------------------------------------------

class Setup(commands.Cog):
    """Module management commands for development purposes."""
    def __init__(self):
        self.last_reload = None


    @commands.command(aliases=['ext', 'modules'])
    @commands.is_owner()
    async def extensions(self, ctx: commands.Context):
        """Shows loaded extensions"""
        cont = 'Enabled modules:\n' + ('\n'.join(bot.extensions) or 'None')
        await ctx.send(cont)


    async def _load_helper(self, ctx: commands.Context[commands.Bot], ext: str, action: Literal['load', 'reload', 'unload'], save: bool=False):
        """Function wrapping module loading in try ... except"""
        if action not in {'load', 'reload', 'unload'}:
            raise TypeError('Bad action argument passed')

        # load/reload/unload_extension
        ref = {'ui': 'ui_components', 'image': 'image_manipulation'}

        if ext in ref:
            module = importlib.import_module(ref[ext])
            importlib.reload(module)

        else:
            func: Callable[[str], None] = getattr(ctx.bot, action + '_extension')

            if func is None:
                raise ValueError('invalid action argument')

            try:
                func(ext)

            except commands.errors.ExtensionError as e:
                print(e)
                await ctx.message.add_reaction('⚠️')
                return

        print('Success')
        emoji = {'load': '☑️', 'reload': '🔄', 'unload': '🚀'}[action]
        await ctx.message.add_reaction(emoji)

        if save:
            self.last_reload = ext


    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: commands.Context, ext: str):
        """Loads an extension"""
        print(f'Loading {ext}...')
        await self._load_helper(ctx, ext, 'load', True)


    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, ext: Optional[str]):
        """Reloads an extension or all extensions"""
        if ext is None:
            if self.last_reload is not None:
                ext = self.last_reload

            else:
                await ctx.send('No module cached.')
                return

        print(f'Reloading {ext}...')
        await self._load_helper(ctx, ext, 'reload', True)


    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, ext: str):
        """Unload an extension"""
        print(f'Unloading {ext}...')
        await self._load_helper(ctx, ext, 'unload')


    @commands.command(aliases=['sd'])
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Terminates the bot connection."""
        await ctx.send('I will be back')
        await bot.close()


class Misc(commands.Cog):
    @commands.command()
    async def ping(self, ctx: commands.Context[commands.Bot]):
        """Pings the bot"""
        await ctx.send(f'Pong! {round(ctx.bot.latency * 1000)}ms')


    @commands.command()
    async def invite(self, ctx: commands.Context[commands.Bot]):
        """Sends an invite link for this bot to the channel"""
        await ctx.send(disnake.utils.oauth_url(ctx.bot.user.id, scopes=('bot', 'applications.commands')))


bot.add_cog(Setup())
bot.add_cog(Misc())
bot.load_extension('SM')


bot.run(TOKEN)
