# this is NOT meant to be __init__.py

import copy
import logging
import logging.handlers
import sys
from collections import abc
from pathlib import Path

import msgspec
from monads.result import Err, Ok, Result

from discord import markdown as md
from disnake import ApplicationCommandType, HTTPException, Locale
from disnake.abc import Messageable

from app import aio, dto, paths, structs
from app.const import Ansi
from app.core.log import JsonFormatter
from app.core.state import I18nStore, State
from app.pack_conversion import collect_items
from app.typeshed import Pathish
from app.utils import async_result, get_source_stats, strip_cwd, try_enum, unset_to_default
from resources import AnyResource, HttpResource

from supermechs.enums import ItemStat

_LOG = logging.getLogger(__name__)


def load_i18n(directory: Pathish, /, i18n: I18nStore) -> None:
    # .glob can fail
    # TODO: is there a better way to wrap .glob?
    try:
        for path in Path(directory).glob(f"*{paths.LOCALE_FILE_EXT}"):
            _LOG.info("Loading locale from %s", path)

            locale = try_enum(path.stem, Locale)

            if locale is None:
                _LOG.warning("%r is not a valid locale", path.stem)
                return

            try:
                data = path.read_bytes()
            except OSError as err:
                _LOG.error("Failed to read %r:", path, exc_info=err)
                return

            try:
                locale_dto = msgspec.toml.decode(data, type=dto.LocaleFileStruct)
            except msgspec.DecodeError as err:
                _LOG.error("Failed to decode %s:", path, exc_info=err)
                return

            for key, entry in locale_dto.stats.items():
                if (stat := try_enum(key, ItemStat)) is None:
                    _LOG.error("Invalid stat key: %s", key)
                    continue
                i18n.stat_l10ns[stat, locale] = entry

            if locale_dto.messages is not msgspec.UNSET:
                for key, message in locale_dto.messages.items():
                    i18n.message_l10ns[key, locale] = message

            if locale_dto.commands is not msgspec.UNSET:
                i18n.command_l10ns[locale.value] = locale_dto.commands

            i18n.locale_info[locale] = structs.LocaleInfo(
                english_name=locale_dto.metadata.english_name,
                local_name=locale_dto.metadata.local_name,
                flag_emoji=unset_to_default(locale_dto.metadata.flag_emoji),
                region=unset_to_default(locale_dto.metadata.region),
            )
    except OSError as exc:
        _LOG.error("Failed to load i18n:", exc_info=exc)


async def sync_commands(state: State, /) -> None:
    _LOG.info("Command sync initiated")
    await state.bot._prepare_application_commands()  # pyright: ignore[reportPrivateUsage]
    _LOG.info("Command sync finished")

    state.command_mentions.clear()

    for command in state.bot._connection._global_application_commands.values():  # pyright: ignore[reportPrivateUsage]
        if command.type is not ApplicationCommandType.chat_input:
            continue

        state.command_mentions[command.name] = md.command_mention(command)


async def init_app_info(state: State, /) -> None:
    match await async_result(state.bot.application_info(), HTTPException):
        case Ok(app_info):
            state.bot_user_info = structs.BotUserInfo(
                owner=app_info.owner,
                team=app_info.team,
                bot_public=app_info.bot_public,
            )
        case Err(exc):
            _LOG.error("Failed to fetch application_info:", exc_info=exc)


async def init_sloc(state: State, /) -> None:
    _LOG.info("Reading source stats")
    state.app_source_stats = await get_source_stats("src")
    _LOG.info("Source stats: %s", state.app_source_stats)


def config_logging() -> None:
    app_rotating_file = paths.LOGS_DIR / "log.jsonl"
    disnake_rotating_file = paths.LOGS_DIR / "disnake_log.jsonl"
    paths.LOGS_DIR.mkdir(exist_ok=True, parents=True)

    LEVEL_TO_COLOR = {
        logging.DEBUG: Ansi.Fore.CYAN + Ansi.Style.DIM,
        logging.INFO: Ansi.Fore.BLUE,
        logging.WARNING: Ansi.Fore.YELLOW,
        logging.ERROR: Ansi.Fore.RED,
        logging.CRITICAL: Ansi.Fore.RED,
    }

    stdout_formatter = logging.Formatter(
        fmt=f"{Ansi.Fore.GREEN}{{asctime}}{Ansi.RESET}"
        f" [{{levelname:^{len('CRITICAL') + len(Ansi.Fore.RED) + len(Ansi.RESET)}}}]"
        f" [{Ansi.Fore.CYAN}{{pathname}}:{{lineno}}{Ansi.RESET}]"
        f" {Ansi.Fore.WHITE}{{message}}{Ansi.RESET}",
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

    def colorize_levelname(record: logging.LogRecord, /) -> logging.LogRecord:
        if (color := LEVEL_TO_COLOR.get(record.levelno)) is None:
            return record

        record = copy.copy(record)
        record.levelname = f"{color}{record.levelname}{Ansi.RESET}"
        return record

    def normalize_record_path(record: logging.LogRecord, /) -> logging.LogRecord:
        if record.pathname == "(unknown file)":
            return record

        try:
            path = strip_cwd(record.pathname)

        except ValueError:
            return record

        record = copy.copy(record)
        record.pathname = path
        return record

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.level = logging.INFO
    stdout_handler.formatter = stdout_formatter
    stdout_handler.filters = [colorize_levelname, normalize_record_path]

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


async def setup_logs_channel(state: State, channel_id: int) -> None:
    try:
        channel = await state.bot.fetch_channel(channel_id)

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


def safe_decode[T](data: abc.Buffer | str, /, *, type: type[T]) -> Result[T, msgspec.DecodeError]:
    # "safe" as in it won't bail with a DecodeError
    try:
        return Ok(msgspec.json.decode(data, type=type))
    except msgspec.DecodeError as exc:
        return Err(exc)


async def load_datapack(
    item_pack_uri: AnyResource,
    gfx_pack_uri: AnyResource | None,
    /,
    state: State,
    http_session: aio.HTTPSession,
) -> None:
    match await aio.read_resource(item_pack_uri, http_session):
        case Err(exc):
            _LOG.error("Could not read %r:", item_pack_uri.uri, exc_info=exc)
            return

        case Ok(item_data):
            pack_decode_result = safe_decode(item_data, type=dto.ItemPackDto)

    if not pack_decode_result:
        _LOG.error("Could not decode ItemPackDto:", exc_info=pack_decode_result.err_value)
        return

    item_pack, images = collect_items(pack_decode_result.ok_value.items)

    _LOG.info(
        "Loaded item pack: reloaded=%d, legacy=%d",
        len(item_pack.reloaded_items),
        len(item_pack.legacy_items),
    )
    state.item_pack = item_pack

    if gfx_pack_uri is None:
        _LOG.warning(f"{gfx_pack_uri=}, no graphics to load")
        return

    match await aio.read_resource(gfx_pack_uri, http_session):
        case Err(exc):
            _LOG.error("Could not read %s:", gfx_pack_uri.uri, exc_info=exc)
            return

        case Ok(gfx_data):
            gfx_decode_result = safe_decode(gfx_data, type=dto.GfxPackDto)

    if not gfx_decode_result:
        _LOG.error("Could not decode GfxPackDto:", exc_info=gfx_decode_result.err_value)
        return

    gfx_dto = gfx_decode_result.ok_value
    sprites: dict[structs.SpriteKey, HttpResource] = {}
    sprite_table = {(sprite.gfx, sprite.reloaded): sprite for sprite in gfx_dto.sprites}

    for image_data in images:
        sprite_dto = sprite_table.get((image_data.image, image_data.reloaded))

        if sprite_dto is None:
            continue

        sprites[image_data.item_id, image_data.tier] = HttpResource.from_uri(
            sprite_dto.image.replace("%url%", gfx_dto.base_url)
        )

    _LOG.info("Loaded sprite pack: images=%d", len(sprites))
    state.sprite_pack = structs.SpritePack(images=sprites)
