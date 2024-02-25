import typing

__all__ = ("command_mention",)

class Commandish(typing.Protocol):
    @property
    def id(self) -> int:
        ...

    @property
    def name(self) -> str:
        ...


def command_mention(command: Commandish, /) -> str:
    """Returns a string allowing to mention a slash command."""
    return f"</{command.name}:{command.id}>"
