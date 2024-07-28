import sys
import typing

from disnake import __version__ as disnake_version
from disnake.utils import utcnow

__all__ = ("disnake_url", "disnake_version", "python_version", "started_at")

started_at: typing.Final = utcnow()
python_version: typing.Final = ".".join(map(str, sys.version_info[:3]))
disnake_url: typing.Final = "https://github.com/DisnakeDev/disnake"
