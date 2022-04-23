from __future__ import annotations

import io
import logging
import traceback
import typing as t

import disnake
import lib_helpers
from config import HOME_GUILD_ID, TEST_GUILDS
from disnake.ext import commands

if t.TYPE_CHECKING:
    from bot import SMBot


logger = logging.getLogger("channel_logs")


class Setup(commands.Cog):
    """Module management commands for development purposes."""
    last_ext = None

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=TEST_GUILDS)
    async def extensions(
        self,
        inter: lib_helpers.ApplicationCommandInteraction,
        action: t.Literal["load", "reload", "unload"] = "reload",
        ext: t.Optional[str] = None
    ) -> None:
        """Extension manager

        Parameters
        -----------
        action: The type of action to perform
        ext: The name of extension to perform action on"""
        if ext is None:
            if self.last_ext is None:
                await inter.send("No extension cached.")
                return

            ext = self.last_ext

        funcs = dict(
            load=inter.bot.load_extension,
            reload=inter.bot.reload_extension,
            unload=inter.bot.unload_extension)

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
    async def ext_autocomplete(
        self, inter: lib_helpers.ApplicationCommandInteraction, input: str
    ) -> list[str]:
        input = input.lower()
        return [ext for ext in inter.bot.extensions if input in ext.lower()]

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=[HOME_GUILD_ID])
    async def shutdown(self, inter: lib_helpers.ApplicationCommandInteraction) -> None:
        """Terminates the bot connection."""
        await inter.send("I will be back", ephemeral=True)
        await inter.bot.close()

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(name="raise", default_permission=False, guild_ids=[HOME_GUILD_ID])
    async def force_error(
        self,
        inter: lib_helpers.ApplicationCommandInteraction,
        exception: str,
        arguments: t.Optional[str] = None
    ) -> None:
        """Explicitly raises provided exception

        Parameters
        -----------
        exception: Name of the exception to raise
        arguments: Optional arguments to pass to the exception"""
        err: type[commands.CommandError] | None = getattr(commands.errors, exception, None)

        if err is None or not issubclass(err, commands.CommandError):
            raise commands.UserInputError("Exception specified has not been found.")

        try:
            raise err(arguments)

        finally:
            await inter.send("Success", ephemeral=True)

    @force_error.autocomplete("exception")
    async def raise_autocomplete(
        self, _: disnake.ApplicationCommandInteraction, input: str
    ) -> list[str]:
        if len(input) < 2:
            return ["Start typing to get options..."]

        input = input.lower()
        return [exc for exc in commands.errors.__all__ if input in exc.lower()][:25]

    @commands.guild_permissions(HOME_GUILD_ID, owner=True)
    @commands.slash_command(default_permission=False, guild_ids=TEST_GUILDS)
    async def database(self, inter: lib_helpers.ApplicationCommandInteraction) -> None:
        """Show info about the database"""
        if inter.bot.engine is None:
            await inter.send("Database is disabled.")
            return

        from pymongo.errors import PyMongoError

        await inter.response.defer()

        try:
            data = await inter.bot.engine.client.server_info()

        except PyMongoError:
            await inter.send("Unable to connect.")
            raise

        data = str(data)

        if len(data) > 2000:
            await inter.send(file=lib_helpers.str_to_file(data))

        else:
            await inter.send(data)


def setup(bot: SMBot) -> None:
    bot.add_cog(Setup())
