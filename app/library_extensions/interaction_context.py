import typing as t

from disnake import ApplicationCommandInteraction, InteractionResponse, MessageInteraction
from typing_extensions import Self, override

if t.TYPE_CHECKING:
    from bot import SMBot


class CommandInteraction(ApplicationCommandInteraction):
    bot: SMBot


MixedInteraction = CommandInteraction | MessageInteraction


class InteractionResponseContext(InteractionResponse):
    pass


class InteractionContext(CommandInteraction):
    """Class meant to bridge Message & CommandInteractions with the purpose of
    enabling easy daisy-chaining command invocations.
    """

    interaction: MixedInteraction

    def __init__(self, inter: MixedInteraction) -> None:
        self.interaction = inter

    @property
    @override
    def response(self) -> InteractionResponseContext:
        return InteractionResponseContext(self)

    @classmethod
    def wrap(cls, inter: MixedInteraction) -> Self:
        if isinstance(inter, cls):
            return inter

        return cls(inter)
