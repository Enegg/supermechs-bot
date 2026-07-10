# this is NOT meant to be __init__.py

import logging
import logging.config
from pathlib import Path

import rtoml

from discord import markdown as md
from disnake import ApplicationCommandType, HTTPException
from disnake.abc import Messageable
from disnake.ext import commands

from app.core import AppState
from app.core.log import patch_file_handler
from app.models.item_pack import ItemPack
from app.models.sprite_pack import SpritePack
from app.typeshed import Bot, Pathish

_LOG = logging.getLogger(__name__)


async def sync_commands(bot: commands.InteractionBot, /) -> None:
    _LOG.info("Command sync initiated")
    await bot._prepare_application_commands()  # pyright: ignore[reportPrivateUsage]
    _LOG.info("Command sync finished")

    AppState.command_mentions.clear()

    for command in bot._connection._global_application_commands.values():  # pyright: ignore[reportPrivateUsage]
        if command.type is not ApplicationCommandType.chat_input:
            continue

        AppState.command_mentions[command.name] = md.command_mention(command)


def config_logging(path: Pathish, /) -> None:
    """Configure the logging module."""
    config = rtoml.load(Path(path))["logging"]
    patch_file_handler()
    logging.config.dictConfig(config)
    logging.captureWarnings(True)


def set_sprite_pack(pack: SpritePack, /) -> None:
    _LOG.info("Storing sprite pack: images=%d", len(pack))
    AppState.sprite_pack = pack


def set_item_pack(pack: ItemPack, /) -> None:
    _LOG.info(
        "Storing item pack: reloaded=%d, legacy=%d",
        len(pack.reloaded_items),
        len(pack.legacy_items),
    )
    AppState.item_pack = pack


async def setup_logs_channel(bot: Bot, channel_id: int) -> None:
    try:
        channel = await bot.fetch_channel(channel_id)

    except HTTPException as exc:
        _LOG.error("Fetching logs channel failed", exc_info=exc)
        return

    if not isinstance(channel, Messageable):
        _LOG.error("Channel is not Messageable")
        return

    _LOG.info("Logs channel: #%s", channel.name)
    AppState.logs_channel = channel
