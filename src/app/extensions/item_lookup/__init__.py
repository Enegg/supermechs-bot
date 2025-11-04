from disnake import Event

from app import ui
from app.plugins_factory import create_plugin

from . import legacy_lookup, reloaded_lookup

plugin = create_plugin(__name__)

plugin.slash_command(name="item")(reloaded_lookup.item_lookup)
plugin.slash_command(name="legacy-item")(legacy_lookup.legacy_item_lookup)


@plugin.listener(Event.message_interaction)
async def on_lookup_interaction(inter: ui.MessageInteraction) -> None:
    if inter.data.custom_id.startswith(reloaded_lookup.ComponentIds.prefix):
        await reloaded_lookup.on_reloaded_lookup_interaction(inter, plugin.logger)

    elif inter.data.custom_id.startswith(legacy_lookup.ComponentIds.prefix):
        await legacy_lookup.on_legacy_lookup_interaction(inter, plugin.logger)


setup, teardown = plugin.create_extension_handlers()
