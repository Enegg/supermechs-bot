# this is NOT meant to be __init__.py

import copy
import importlib.util
import logging
import logging.handlers
import pkgutil
import sys
from collections import abc
from functools import partial
from pathlib import Path

import msgspec

from discord import markdown as md
from disnake import ApplicationCommandType, HTTPException, Locale
from disnake.abc import Messageable

from app import aio, dto, paths, structs
from app.async_utils import gather
from app.const import Ansi
from app.core.state import I18nStore, State
from app.pack_conversion import collect_items
from app.typeshed import Bot, Pathish, ResultTuple
from app.utils import (
    JsonFormatter,
    async_result,
    get_source_stats,
    read_and_parse_file,
    strip_cwd,
    try_enum,
    unset_to_default,
)
from resources import AnyResource, HttpResource

from supermechs.enums import ItemStat

_LOG = logging.getLogger(__name__)


def load_plugins(package: str, /, state: State) -> None:
    if (spec := importlib.util.find_spec(package)) is None:
        _LOG.error("Unable to find root module %r", package)
        return

    if spec.submodule_search_locations is None:
        _LOG.error("Module %r is not a package", package)
        return

    # TODO: this isn't enough to make this callable more than once
    state.loaded_plugins.clear()

    for module_info in pkgutil.iter_modules(spec.submodule_search_locations, spec.name + "."):
        plugin_name = module_info.name
        sys.modules.pop(plugin_name, None)

        try:
            module = importlib.import_module(plugin_name)
        except ImportError as exc:
            _LOG.error("Importing %r failed:", plugin_name, exc_info=exc)
            continue
        except Exception as exc:
            _LOG.error("Exception while executing %r:", plugin_name, exc_info=exc)
            continue

        setup: abc.Callable[[Bot], None] | None = getattr(module, "setup", None)

        if setup is None:
            del sys.modules[plugin_name]
            _LOG.error("Plugin %r has no setup()", plugin_name)
            continue

        try:
            setup(state.bot)
        except Exception as exc:
            del sys.modules[plugin_name]
            _LOG.error("%s.setup() raised an exception:", plugin_name, exc_info=exc)
            # TODO: _remove_module_references
            # TODO: _call_module_finalizers
            continue

        state.loaded_plugins.append(plugin_name)


def load_i18n(directory: Pathish, /, i18n: I18nStore) -> None:
    i18n.locale_info.clear()
    i18n.stat_l10ns.clear()
    i18n.message_l10ns.clear()
    i18n.command_l10ns.clear()
    # .glob can fail
    # TODO: is there a better way to wrap .glob?
    try:
        for path in Path(directory).glob(f"*{paths.LOCALE_FILE_EXT}"):
            _LOG.info("Loading locale from %s", path)

            locale = try_enum(path.stem, Locale)

            if locale is None:
                _LOG.warning("%r is not a valid locale", path.stem)
                continue

            match read_and_parse_file(path, type=dto.LocaleFileStruct):
                case None, exc:
                    _LOG.error("Failed to read %r:", path, exc_info=exc)
                    continue

                case locale_dto, None:
                    pass

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
    try:
        app_info = await state.bot.application_info()
    except HTTPException as exc:
        _LOG.error("Failed to fetch application_info:", exc_info=exc)
    else:
        state.bot_user_info = structs.BotUserInfo(
            owner=app_info.owner,
            team=app_info.team,
            bot_public=app_info.bot_public,
        )


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
    match await async_result(state.bot.fetch_channel(channel_id), HTTPException):
        case None, exc:
            _LOG.error("Fetching logs channel failed", exc_info=exc)

        case Messageable() as channel, None:
            _LOG.info("Logs channel: #%s", channel.name)
            state.logs_channel = channel

        case channel, None:
            _LOG.error(
                "Channel is not Messageable: type=%s",
                # abc.PrivateChannel does not expose .type, but DMChannel does
                channel.type.name,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownArgumentType]
            )


def safe_decode[T](
    data: abc.Buffer | str, /, *, type: type[T]
) -> ResultTuple[T, msgspec.DecodeError]:
    # "safe" as in it won't bail with a DecodeError
    try:
        return msgspec.json.decode(data, type=type), None
    except msgspec.DecodeError as exc:
        return None, exc


async def load_datapack(
    item_pack_uri: AnyResource,
    gfx_pack_uri: AnyResource | None,
    /,
    state: State,
    http_session: aio.HTTPSession,
) -> None:
    if gfx_pack_uri is None:
        item_pack_resource = await aio.read_resource(item_pack_uri, http_session)
        gfx_dto = None
        _LOG.warning(f"{gfx_pack_uri=}, no graphics to load")
    else:
        item_pack_resource, gfx_pack_resource = await gather(
            partial(aio.read_resource, item_pack_uri, http_session),
            partial(aio.read_resource, gfx_pack_uri, http_session),
        )

        match gfx_pack_resource:
            case None, exc:
                _LOG.error("Could not read %s:", gfx_pack_uri.uri, exc_info=exc)
                return

            case gfx_data, None:
                match safe_decode(gfx_data, type=dto.GfxPackDto):
                    case None, exc:
                        _LOG.error("Could not decode GfxPackDto:", exc_info=exc)
                        return

                    case gfx_dto, None:
                        pass

    match item_pack_resource:
        case None, exc:
            _LOG.error("Could not read %r:", item_pack_uri.uri, exc_info=exc)
            return

        case item_data, None:
            match safe_decode(item_data, type=dto.ItemPackDto):
                case None, exc:
                    _LOG.error("Could not decode ItemPackDto:", exc_info=exc)
                    return

                case pack_dto, None:
                    item_pack, images = collect_items(pack_dto.items)

    _LOG.info(
        "Loaded item pack: reloaded=%d, legacy=%d",
        len(item_pack.reloaded_items),
        len(item_pack.legacy_items),
    )
    state.item_pack = item_pack

    if gfx_dto is None:
        return

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
