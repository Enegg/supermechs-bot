__all__ = ("Markdown",)


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
    def strip_codeblock(text: str, /) -> str:
        """Return text stripped from codeblock syntax."""
        text = text.removeprefix("```").removesuffix("```")
        lang, sep, stripped = text.partition("\n")

        # coffeescript seems to be the longest lang name discord accepts
        if sep and len(lang) <= len("coffeescript"):
            return stripped

        return text
