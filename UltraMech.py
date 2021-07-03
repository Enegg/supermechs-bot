from __future__ import annotations


from typing import *  # type: ignore
import os


import discord
from discord.ext import commands


from config import PREFIX_LOCAL, PREFIX_HOST, LOGS_CHANNEL



TOKEN: str | None = os.environ.get('TOKEN')

if TOKEN is not None:
    hosted = True

else:
    import sys, importlib

    token_module = importlib.import_module('TOKEN')
    TOKEN = getattr(token_module, 'TOKEN', None)

    if not TOKEN:
        raise EnvironmentError('Not running localy and TOKEN is not an environment variable')

    if args := frozenset(sys.argv[1:]):
        hosted = 'host' in args

    else:
        hosted = False


def prefix_handler(bot: HostedBot, msg: discord.Message) -> Union[str, list[str]]:
    prefix = (PREFIX_LOCAL, PREFIX_HOST)[bot.hosted]

    if isinstance(msg.channel, discord.DMChannel):
        return [prefix, '']

    return prefix

# ------------------------------------------ Bot init ------------------------------------------

class HostedBot(commands.Bot):
    def __init__(self, hosted: bool=False, **options):
        super().__init__(**options)
        self.hosted = hosted

intents = discord.Intents(guilds=True, members=True, emojis=True, messages=True, reactions=True)
bot = HostedBot(command_prefix=prefix_handler, hosted=hosted, intents=intents)

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


    async def _load_helper(self, ctx: commands.Context, ext: str, action: Literal['load', 'reload', 'unload'], save: bool=False):
        """Function wrapping module loading in try ... except"""
        if action not in {'load', 'reload', 'unload'}:
            raise TypeError('Bad action argument passed')

        # load/reload/unload_extension
        func: Callable[[str], None] = getattr(ctx.bot, action + '_extension')

        if func is None:
            raise ValueError('invalid action argument')

        try:
            func(ext)

        except commands.errors.ExtensionError as e:
            print(e)
            await ctx.message.add_reaction('⚠️')

        else:
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
        await bot.logout()


bot.add_cog(Setup())
bot.load_extension('SM')

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    e = commands.errors
    simple_reactions = {e.CommandNotFound: '❓', e.CheckFailure: '🔒', e.CommandOnCooldown: '🕓'}
    simple_reactions: dict[type[commands.CommandError], str]

    if type(error) in simple_reactions:
        await ctx.message.add_reaction(simple_reactions[type(error)])
        return

    if isinstance(error, e.BadArgument):
        await ctx.send(error, delete_after=5.0)

    else:
        print(error)

        if bot.hosted:
            channel = bot.get_channel(LOGS_CHANNEL)
            assert isinstance(channel, discord.TextChannel)
            await channel.send(f'{error}\n{type(error)}')

@bot.event
async def on_ready():
    text = f'{bot.user.name} is online'
    print(text, '-' * len(text), sep='\n')

    if bot.hosted:
        channel = bot.get_channel(LOGS_CHANNEL)
        assert isinstance(channel, discord.TextChannel)
        await channel.send("I'm back online")
        activity = {'name': 'SuperMechs', 'url': 'https://workshop-unlimited.vercel.app/',
                    'type': discord.ActivityType.playing}

    else:
        activity = {'name': 'under maintenance', 'type': discord.ActivityType.playing}

    await bot.change_presence(activity=discord.Activity(**activity))

bot.run(TOKEN)
