import anyio

from app.disnake_types import CommandInteraction
from discord.commands import register_cancellable

from app.plugins_factory import create_dev_plugin

plugin = create_dev_plugin(__name__)


@register_cancellable
@plugin.slash_command()
async def test_cancellation(inter: CommandInteraction, time: int) -> None:
    await inter.response.send_message(f"Sleeping for {time}s")

    try:
        await anyio.sleep(time)

    finally:
        with anyio.CancelScope(shield=True):
            await inter.edit_original_response("Finished!")


setup, teardown = plugin.create_extension_handlers()
