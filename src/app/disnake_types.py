from typing import TypeAlias

import disnake
import disnake_plugins
from disnake.ext import commands

Bot: TypeAlias = commands.InteractionBot
Plugin: TypeAlias = disnake_plugins.Plugin[Bot]
Interaction: TypeAlias = disnake.Interaction[Bot]
CommandInteraction: TypeAlias = disnake.CommandInteraction[Bot]
MessageInteraction: TypeAlias = disnake.MessageInteraction[Bot]
ModalInteraction: TypeAlias = disnake.ModalInteraction[Bot]
