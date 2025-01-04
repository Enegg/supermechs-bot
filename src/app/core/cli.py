import pathlib

import attrs
import datargs

from app import paths

__all__ = ("ARGV",)


@attrs.define
class Argv:
    dotenv_path: pathlib.Path = paths.DEV_ENV
    indev: bool = __debug__
    debug_command_sync: bool = __debug__


ARGV = datargs.parse(Argv)
