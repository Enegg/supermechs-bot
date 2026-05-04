import argparse
import os
import pathlib
import types
from collections import abc
from typing import Final

import attrs
import dotenv

from app import paths
from app.class_utils import MappingParser
from resources import AnyResource, from_uri

__all__ = ("CONFIG",)


@attrs.frozen(kw_only=True)
class Config:
    bot_token: str = attrs.field(repr=lambda _: "***")
    """Discord bot token."""
    dev_guild_id: int
    """ID of a guild dev-only commands will be registered to."""
    indev: bool = __debug__
    """Whether the bot is in development mode."""
    debug_command_sync: bool = __debug__
    """Whether disnake should log detailed sync info."""
    logs_channel_id: int | None = None
    """ID of a text channel log messages will be sent to."""
    item_pack_uri: AnyResource | None = None
    """Path/URL of an item pack."""
    gfx_pack_uri: AnyResource | None = None
    """Path/URL of a graphics pack."""
    user_input_timeout: float = 180.0
    """Time in seconds after which various forms of user input are disabled."""

    @property
    def test_guild_ids(self) -> abc.Sequence[int]:
        """The IDs of only guilds the bot will register commands in while in dev mode."""
        return (self.dev_guild_id,)


def get_config() -> Config:
    _parser = argparse.ArgumentParser("supermechs-bot")
    _parser.add_argument("--token", action="store", default="", help="Bot token to use.")
    _parser.add_argument(
        "--env",
        action="store",
        type=pathlib.Path,
        default=paths.DEV_ENV,
        help=f"Path to a .env file. Default: {paths.DEV_ENV}",
    )
    _parser.add_argument(
        "--dev-guild",
        dest="dev_guild_id",
        action="store",
        type=int,
        default=argparse.SUPPRESS,
        help="ID of a guild dev-only commands will be registered to.",
        metavar="ID",
    )
    _parser.add_argument(
        "--item-pack",
        dest="item_pack_uri",
        action="store",
        type=from_uri,
        default=argparse.SUPPRESS,
        help="Path/URL of an item pack.",
        metavar="URI",
    )
    _parser.add_argument(
        "--gfx-pack",
        dest="gfx_pack_uri",
        action="store",
        type=from_uri,
        default=argparse.SUPPRESS,
        help="Path/URL of a graphics pack.",
        metavar="URI",
    )

    ns = _parser.parse_args(namespace=types.SimpleNamespace())
    assert isinstance(ns.env, pathlib.Path)
    dotenv.load_dotenv(ns.env)
    return MappingParser(vars(ns), os.environ).structure(Config)


CONFIG: Final = get_config()

if __name__ == "__main__":
    import rich

    rich.print(CONFIG)
