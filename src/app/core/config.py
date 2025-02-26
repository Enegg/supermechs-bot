import os
from collections import abc

import attrs
import dotenv

from app.class_utils import ByteSize, MappingParser

from .cli import ARGV

from supermechs.gamerules import BuildRules

__all__ = ("CONFIG",)


@attrs.frozen(kw_only=True)
class Config:
    bot_token: str = attrs.field(repr=lambda _: "***")
    """Discord bot token."""
    home_guild_id: int
    """ID of a guild dev-only commands will be registered to."""
    indev: bool = __debug__
    """Whether the bot is in development mode."""
    debug_command_sync: bool = __debug__
    """Whether disnake should log detailed sync info."""
    logs_channel_id: int | None = None
    """ID of a text channel log messages will be sent to."""
    default_pack_url: str = (
        "https://gist.githubusercontent.com/ctrlraul/3b5669e4246bc2d7dc669d484db89062/raw"
    )
    """Path/URL of the default item pack."""
    missing_image_url: str = (
        "https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png"
    )
    """Path/URL of a placeholder image."""
    max_image_size: ByteSize = ByteSize(25 * 1024 * 1024)
    """Maximum allowed size of an image fetched from user source."""
    chunk_size: ByteSize = ByteSize(1024 * 1024)
    """Size of a chunk in iterative download."""
    build_rules: BuildRules = BuildRules.default
    """Set of rules mech builds must obey."""
    user_input_timeout: float = 180.0
    """Time in seconds after which various forms of user input are disabled."""

    @property
    def test_guild_ids(self) -> abc.Sequence[int]:
        """The IDs of only guilds the bot will register commands in while in dev mode."""
        return (self.home_guild_id,)


dotenv.load_dotenv(ARGV.dotenv_path)
CONFIG = MappingParser(
    attrs.asdict(ARGV),
    os.environ,
).structure(Config)


if __name__ == "__main__":
    print(CONFIG)
