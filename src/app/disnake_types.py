from typing import TypeAlias

import disnake
from disnake.ext import commands

Bot: TypeAlias = commands.InteractionBot
Interaction: TypeAlias = disnake.Interaction[Bot]
CommandInteraction: TypeAlias = disnake.CommandInteraction[Bot]
MessageInteraction: TypeAlias = disnake.MessageInteraction[Bot]
ModalInteraction: TypeAlias = disnake.ModalInteraction[Bot]
