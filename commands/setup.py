from __future__ import annotations

import io
import logging
import traceback
import typing as t

import disnake
from config import TEST_GUILDS
from disnake.ext import commands
from lib_helpers import str_to_file

if t.TYPE_CHECKING:
    from bot import SMBot


logger = logging.getLogger("channel_logs")


class Setup(commands.Cog):
    """Module management commands for development purposes."""

    last_ext = None

    def __init__(self, bot: SMBot) -> None:
        self.bot = bot

    @commands.slash_command(guild_ids=TEST_GUILDS)
    @commands.is_owner()
    async def ext(
        self,
        inter: disnake.CommandInteraction,
        action: t.Literal["load", "reload", "unload"] = "reload",
        ext: t.Optional[str] = None,
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
            load=self.bot.load_extension,
            reload=self.bot.reload_extension,
            unload=self.bot.unload_extension,
        )

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

    @ext.autocomplete("ext")
    async def ext_autocomplete(self, inter: disnake.CommandInteraction, input: str) -> list[str]:
        input = input.lower()
        return [ext for ext in self.bot.extensions if input in ext.lower()]

    @commands.slash_command(guild_ids=TEST_GUILDS)
    @commands.is_owner()
    async def shutdown(self, inter: disnake.CommandInteraction) -> None:
        """Terminates the bot connection."""
        await inter.send("I will be back", ephemeral=True)
        await self.bot.close()

    @commands.slash_command(name="raise", guild_ids=TEST_GUILDS)
    @commands.is_owner()
    async def force_error(
        self,
        inter: disnake.CommandInteraction,
        exception: str,
        arguments: t.Optional[str] = None,
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
    async def raise_autocomplete(self, _: disnake.CommandInteraction, input: str) -> list[str]:
        if len(input) < 2:
            return ["Start typing to get options..."]

        input = input.lower()
        return [exc for exc in commands.errors.__all__ if input in exc.lower()][:25]

    # @commands.slash_command(guild_ids=TEST_GUILDS)
    # @commands.is_owner()
    # async def database(self, inter: disnake.CommandInteraction) -> None:
    #     """Show info about the database"""
    #     if self.bot.engine is None:
    #         await inter.send("Database is disabled.")
    #         return

    #     from pymongo.errors import PyMongoError

    #     await inter.response.defer()

    #     try:
    #         data = await self.bot.engine.client.server_info()

    #     except PyMongoError:
    #         await inter.send("Unable to connect.")
    #         raise

    #     data = str(data)

    #     if len(data) > 2000:
    #         await inter.send(file=str_to_file(data))

    #     else:
    #         await inter.send(data)

    @commands.slash_command(name="eval", guild_ids=TEST_GUILDS)
    @commands.is_owner()
    async def eval_(self, inter: disnake.CommandInteraction, input: str) -> None:
        """Evaluates the given input as code.

        Parameters
        ----------
        input: code to execute."""
        input = input.strip()

        out = io.StringIO()

        def print_(*args: t.Any, **kwargs: t.Any) -> None:
            print(*args, **kwargs, file=out)

        output = eval(input, globals() | {"bot": self.bot, "inter": inter, "print": print_})
        std = out.getvalue()

        if output is None or not std:
            msg = f"```\n{std or output}```"

        else:
            msg = "```\n" f"{output}```\n" "**stdout:**\n" "```\n" f"{std}```"

        if len(msg) > 2000:
            file = str_to_file(msg.strip("` "))
            await inter.send(file=file, ephemeral=True)

        else:
            await inter.send(
                msg,
                allowed_mentions=disnake.AllowedMentions.none(),
                ephemeral=True,
            )


def setup(bot: SMBot) -> None:
    bot.add_cog(Setup(bot))
