import os
from collections import abc
from typing import Final

import attrs
import dotenv

from app.cattrs_utils import ByteSize
from app.class_utils import MappingParser
from resources import AnyResource

from .cli import ARGV

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
    """Path/URL of the default item pack."""
    gfx_pack_uri: AnyResource | None = None
    """Path/URL of independent graphics for item pack."""
    max_image_size: ByteSize = ByteSize(25 * 1024 * 1024)
    """Maximum allowed size of an image fetched from user source."""
    chunk_size: ByteSize = ByteSize(1024 * 1024)
    """Size of a chunk in iterative download."""
    user_input_timeout: float = 180.0
    """Time in seconds after which various forms of user input are disabled."""

    @property
    def test_guild_ids(self) -> abc.Sequence[int]:
        """The IDs of only guilds the bot will register commands in while in dev mode."""
        return (self.dev_guild_id,)


dotenv.load_dotenv(ARGV.dotenv_path)
CONFIG: Final = MappingParser(
    attrs.asdict(ARGV),
    os.environ,
).structure(Config)


if __name__ == "__main__":
    print(CONFIG)
