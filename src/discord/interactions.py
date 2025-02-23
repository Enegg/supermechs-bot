from disnake import Client, CommandInteraction


def inter_to_mention(inter: CommandInteraction[Client], /) -> str:
    """Return a string mentioning a slash command which invoked the interaction."""
    return f"</{inter.application_command.qualified_name}:{inter.data.id}>"
