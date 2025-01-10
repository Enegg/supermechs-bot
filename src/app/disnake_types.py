from typing import TypeAlias

import disnake
from disnake.ext import commands

Interaction: TypeAlias = disnake.Interaction[commands.InteractionBot]
CommandInteraction: TypeAlias = disnake.CommandInteraction[commands.InteractionBot]
MessageInteraction: TypeAlias = disnake.MessageInteraction[commands.InteractionBot]
ModalInteraction: TypeAlias = disnake.ModalInteraction[commands.InteractionBot]
