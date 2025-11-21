import disnake
from disnake.ext import commands

type Bot = commands.InteractionBot
type Interaction = disnake.Interaction[Bot]
type CommandInteraction = disnake.CommandInteraction[Bot]
type MessageInteraction = disnake.MessageInteraction[Bot]
type ModalInteraction = disnake.ModalInteraction[Bot]
