import sys
from typing import Final

import psutil

import disnake

APP_PROCESS: Final = psutil.Process()
DISNAKE_URL: Final = "https://github.com/DisnakeDev/disnake"
DISNAKE_VERSION: Final = disnake.__version__
FALLBACK_LOCALE: Final = disnake.Locale.en_US
PYTHON_VERSION: Final = ".".join(map(str, sys.version_info[:3]))


class Ansi:
    # https://xscript.net/ansi-color-codes
    RESET: Final = "\x1b[0m"

    class Style:
        BOLD: Final = "\x1b[1m"
        DIM: Final = "\x1b[2m"
        ITALIC: Final = "\x1b[3m"
        UNDERLINE: Final = "\x1b[4m"
        STRIKETHROUGH: Final = "\x1b[9m"

    class Fore:
        BLACK: Final = "\x1b[30m"
        RED: Final = "\x1b[31m"
        GREEN: Final = "\x1b[32m"
        YELLOW: Final = "\x1b[33m"
        BLUE: Final = "\x1b[34m"
        MAGENTA: Final = "\x1b[35m"
        CYAN: Final = "\x1b[36m"
        WHITE: Final = "\x1b[37m"

        BRIGHT_BLACK: Final = "\x1b[90m"
        BRIGHT_RED: Final = "\x1b[91m"
        BRIGHT_GREEN: Final = "\x1b[92m"
        BRIGHT_YELLOW: Final = "\x1b[93m"
        BRIGHT_BLUE: Final = "\x1b[94m"
        BRIGHT_MAGENTA: Final = "\x1b[95m"
        BRIGHT_CYAN: Final = "\x1b[96m"
        BRIGHT_WHITE: Final = "\x1b[97m"

        @staticmethod
        def rgb(r: int, g: int, b: int, /) -> str:
            """24-bit color. r, g, b must be in range 0-255."""
            return f"\x1b[38;2;{r};{g};{b}m"

    class Back:
        BLACK: Final = "\x1b[40m"
        RED: Final = "\x1b[41m"
        GREEN: Final = "\x1b[42m"
        YELLOW: Final = "\x1b[43m"
        BLUE: Final = "\x1b[44m"
        MAGENTA: Final = "\x1b[45m"
        CYAN: Final = "\x1b[46m"
        WHITE: Final = "\x1b[47m"

        BRIGHT_BLACK: Final = "\x1b[100m"
        BRIGHT_RED: Final = "\x1b[101m"
        BRIGHT_GREEN: Final = "\x1b[102m"
        BRIGHT_YELLOW: Final = "\x1b[103m"
        BRIGHT_BLUE: Final = "\x1b[104m"
        BRIGHT_MAGENTA: Final = "\x1b[105m"
        BRIGHT_CYAN: Final = "\x1b[106m"
        BRIGHT_WHITE: Final = "\x1b[107m"

        @staticmethod
        def rgb(r: int, g: int, b: int, /) -> str:
            """24-bit color. r, g, b must be in range 0-255."""
            return f"\x1b[48;2;{r};{g};{b}m"
