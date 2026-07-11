# this is NOT meant to be __init__.py

import logging
import logging.handlers
import sys

from discord import markdown as md
from disnake import ApplicationCommandType, HTTPException
from disnake.abc import Messageable
from disnake.ext import commands

from app import paths
from app.core import AppState
from app.core.log import JsonFormatter, normalize_record_path
from app.models.item_pack import ItemPack
from app.models.sprite_pack import SpritePack
from app.typeshed import Bot

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


def config_logging() -> None:
    """Configure the logging module."""
    app_rotating_file = paths.LOGS_DIR / "log.jsonl"
    disnake_rotating_file = paths.LOGS_DIR / "disnake_log.jsonl"
    paths.LOGS_DIR.mkdir(exist_ok=True, parents=True)

    simple_formatter = logging.Formatter(
        fmt="{asctime} [{levelname:^8}] [{pathname}:{lineno}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )
    json_formatter = JsonFormatter(fmt_keys={
        "timestamp": "timestamp",
        "level": "levelname",
        "message": "message",
        "logger": "name",
        "module": "module",
        "function": "funcName",
        "line": "lineno",
    })  # fmt: skip

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.level = logging.INFO
    stdout_handler.formatter = simple_formatter
    stdout_handler.filters = [normalize_record_path]

    app_file_handler = logging.handlers.RotatingFileHandler(
        app_rotating_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
    )
    app_file_handler.level = logging.DEBUG
    app_file_handler.formatter = json_formatter
    app_file_handler.filters = [normalize_record_path]

    disnake_file_handler = logging.handlers.RotatingFileHandler(
        disnake_rotating_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
    )
    disnake_file_handler.level = logging.DEBUG
    disnake_file_handler.formatter = json_formatter
    disnake_file_handler.filters = [normalize_record_path]

    disnake_logger = logging.getLogger("disnake")
    disnake_logger.level = logging.DEBUG
    disnake_logger.handlers = [disnake_file_handler]
    disnake_logger.propagate = False

    logging.root.level = logging.INFO
    logging.root.handlers = [stdout_handler, app_file_handler]
    logging.root.filters = [normalize_record_path]
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
