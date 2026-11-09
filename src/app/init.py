# this is NOT meant to be __init__.py

import logging
import logging.handlers
import sys
from collections import abc

import msgspec
from monads.result import Err, Ok

from discord import markdown as md
from disnake import ApplicationCommandType, Client, HTTPException
from disnake.abc import Messageable
from disnake.ext import commands

from app import aio, dto, paths, structs
from app.core import state
from app.core.log import JsonFormatter, normalize_record_path
from app.pack_conversion import collect_items
from app.utils import get_sloc
from resources import AnyResource, HttpResource

_LOG = logging.getLogger(__name__)


async def sync_commands(bot: commands.InteractionBot, /) -> None:
    _LOG.info("Command sync initiated")
    await bot._prepare_application_commands()  # pyright: ignore[reportPrivateUsage]
    _LOG.info("Command sync finished")

    state.command_mentions.clear()

    for command in bot._connection._global_application_commands.values():  # pyright: ignore[reportPrivateUsage]
        if command.type is not ApplicationCommandType.chat_input:
            continue

        state.command_mentions[command.name] = md.command_mention(command)


async def init_app_info() -> None:
    app_info = await state.BOT.application_info()
    state.bot_user_info = structs.BotUserInfo(
        owner=app_info.owner,
        team=app_info.team,
        bot_public=app_info.bot_public,
    )


async def init_sloc() -> None:
    state.app_sloc = await get_sloc("src")


def config_logging() -> None:
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


async def setup_logs_channel(client: Client, channel_id: int) -> None:
    try:
        channel = await client.fetch_channel(channel_id)

    except HTTPException as exc:
        _LOG.error("Fetching logs channel failed", exc_info=exc)
        return

    if not isinstance(channel, Messageable):
        _LOG.error(
            "Channel is not Messageable: type=%s",
            # abc.PrivateChannel does not expose .type, but DMChannel does
            channel.type.name,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType]
        )
        return

    _LOG.info("Logs channel: #%s", channel.name)
    state.logs_channel = channel


def safe_decode[T](data: abc.Buffer | str, /, *, type: type[T]) -> T | None:
    # "safe" as in it won't bail with a DecodeError
    try:
        return msgspec.json.decode(data, type=type)

    except msgspec.DecodeError as exc:
        _LOG.error("Could not decode %s:", type.__name__, exc_info=exc)
        return None


async def load_datapack(
    item_pack_uri: AnyResource, gfx_pack_uri: AnyResource | None, /, session: aio.HTTPSession
) -> None:
    match await aio.read_resource(item_pack_uri, session):
        case Err(exc):
            _LOG.error("Could not read %s:", item_pack_uri.uri, exc_info=exc)
            return

        case Ok(data):
            pack_dto = safe_decode(data, type=dto.ItemPackDto)

    if pack_dto is None:
        return

    item_groups = collect_items(pack_dto.items)
    item_pack = structs.ItemPack(
        reloaded_items=item_groups.reloaded,
        legacy_items=item_groups.legacy,
        hidden_items=item_groups.hidden,
    )
    _LOG.info(
        "Loaded item pack: reloaded=%d, legacy=%d",
        len(item_pack.reloaded_items),
        len(item_pack.legacy_items),
    )
    state.item_pack = item_pack

    if gfx_pack_uri is None:
        _LOG.warning(f"{gfx_pack_uri=}, no graphics to load")
        return

    match await aio.read_resource(gfx_pack_uri, session):
        case Err(exc):
            _LOG.error("Could not read %s:", gfx_pack_uri.uri, exc_info=exc)
            return

        case Ok(gfx_data):
            gfx_dto = safe_decode(gfx_data, type=dto.GfxPackDto)

    if gfx_dto is None:
        return

    sprite_pack: structs.SpritePack = {}
    sprite_table = {(sprite.gfx, sprite.reloaded): sprite for sprite in gfx_dto.sprites}

    for image_data in item_groups.images:
        sprite_dto = sprite_table.get((image_data.image, image_data.reloaded))

        if sprite_dto is None:
            continue

        sprite_pack[image_data.item_id, image_data.tier] = HttpResource.from_uri(
            sprite_dto.image.replace("%url%", gfx_dto.base_url)
        )

    _LOG.info("Loaded sprite pack: images=%d", len(sprite_pack))
    state.sprite_pack = sprite_pack
