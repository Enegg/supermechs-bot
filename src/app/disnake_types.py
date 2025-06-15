from typing import Protocol

import disnake
from disnake import Locale
from disnake.ext import commands

type Bot = commands.InteractionBot
type Interaction = disnake.Interaction[Bot]
type CommandInteraction = disnake.CommandInteraction[Bot]
type MessageInteraction = disnake.MessageInteraction[Bot]


class HasLocale(Protocol):
    @property
    def locale(self) -> Locale: ...
