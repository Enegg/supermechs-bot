from __future__ import annotations

import io
import logging
import typing as t
from traceback import print_exception

from disnake import AllowedMentions, CommandInteraction
from disnake.ext import commands

from app import TEST_GUILDS
from app.lib_helpers import str_to_file

if t.TYPE_CHECKING:
    from app.bot import SMBot

logger = logging.getLogger(f"main.{__name__}")


class Setup(commands.Cog):
    """Module management commands for development purposes."""

    def __init__(self, bot: SMBot) -> None:
        self.bot = bot
        self.last_ext: str | None = None

    @commands.slash_command(guild_ids=TEST_GUILDS)
    @commands.default_member_permissions(administrator=True)
    @commands.is_owner()
    async def ext(
        self,
        inter: CommandInteraction,
        action: t.Literal["load", "reload", "unload"] = "reload",
        ext: str | None = None,
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
                sio.write("An error occured:\n```py\n")
                print_exception(type(error), error, error.__traceback__, file=sio)
                sio.write("```")
            await inter.send(sio.getvalue(), ephemeral=True)

        else:
            await inter.send("Success", ephemeral=True)

            self.last_ext = ext

    @ext.autocomplete("ext")
    async def ext_autocomplete(self, inter: CommandInteraction, input: str) -> list[str]:
        input = input.lower()
        return [ext for ext in self.bot.extensions if input in ext.lower()]

    @commands.slash_command(guild_ids=TEST_GUILDS)
    @commands.default_member_permissions(administrator=True)
    @commands.is_owner()
    async def shutdown(self, inter: CommandInteraction) -> None:
        """Terminates the bot connection."""
        await inter.send("I will be back", ephemeral=True)
        await self.bot.close()

    @commands.slash_command(name="raise", guild_ids=TEST_GUILDS)
    @commands.default_member_permissions(administrator=True)
    @commands.is_owner()
    async def force_error(
        self,
        inter: CommandInteraction,
        exception: str,
        arguments: str | None = None,
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
    async def raise_autocomplete(self, _: CommandInteraction, input: str) -> list[str]:
        if len(input) < 2:
            return ["Start typing to get options..."]

        input = input.lower()
        return [exc for exc in commands.errors.__all__ if input in exc.lower()][:25]

    @commands.slash_command(name="eval", guild_ids=TEST_GUILDS)
    @commands.default_member_permissions(administrator=True)
    @commands.is_owner()
    async def eval_(self, inter: CommandInteraction, input: str) -> None:
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
            msg = f"```\n{output}```\n**stdout:**\n```\n{std}```"

        if len(msg) > 2000:
            file = str_to_file(msg.strip("` "))
            await inter.send(file=file, ephemeral=True)

        else:
            await inter.send(
                msg,
                allowed_mentions=AllowedMentions.none(),
                ephemeral=True,
            )


def setup(bot: SMBot) -> None:
    bot.add_cog(Setup(bot))
    logger.info('Cog "Setup" loaded')
