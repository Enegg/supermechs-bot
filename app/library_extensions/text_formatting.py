import string
import typing as t
from typing_extensions import LiteralString

from disnake import Locale, LocalizationProtocol

__all__ = ("SPACE", "Markdown", "monospace", "localized_text", "sanitize_filename")


SPACE: t.Final = "\u2800"
"""Invisible character discord does not truncate."""


class Markdown:
    """Namespace class for functions related to markdown syntax."""

    @staticmethod
    def hyperlink(text: str, url: str) -> str:
        """Return a hyperlink to a URL."""
        return f"[{text}]({url})"

    @staticmethod
    def codeblock(text: str, lang: str = "") -> str:
        """Return text formatted with a codeblock."""
        return f"```{lang}\n{text}```"

    @staticmethod
    def strip_codeblock(text: str) -> str:
        """Return text stripped from codeblock syntax."""
        text = text.removeprefix("```").removesuffix("```")
        lang, sep, stripped = text.partition("\n")

        # coffeescript seems to be the longest lang name discord accepts
        if sep and len(lang) <= len("coffeescript"):
            return stripped

        return text


class monospace:
    """Collection of monospace string constants."""

    lowercase: LiteralString = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
    uppercase: LiteralString = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"  # noqa: RUF001
    letters: LiteralString = lowercase + uppercase
    digits: LiteralString = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"  # noqa: RUF001

    table = str.maketrans(string.digits + string.ascii_letters, digits + letters)


def localized_text(content: str, key: str, i18n: LocalizationProtocol, locale: Locale) -> str:
    """Grabs text from a i18n provider under specified key, or fallbacks to content."""
    locs = i18n.get(key) or {}
    return locs.get(str(locale), content)


def sanitize_filename(filename: str, extension: str) -> str:
    """Converts spaces to underscores, and adds extension if one isn't there."""
    filename = filename.replace(" ", "_")

    if not filename.endswith(extension):
        filename += extension

    return filename.lower()
