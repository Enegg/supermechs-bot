import logging
import pathlib
from collections import abc

import orjson
from cattrs import ClassValidationError

from app.core import CONFIG
from app.models.player import PartialPlayer, Player
from app.typeshed import Pathish

from .converter import converter

STATE_FILE = "state_dev" if CONFIG.indev else "state"
OLD_STATE_FILE = STATE_FILE + ".old"
_LOG = logging.getLogger(__name__)


# ---------------------------------------------- load ----------------------------------------------
def load_state(path: Pathish, /) -> list[PartialPlayer]:
    path = pathlib.Path(path, STATE_FILE)
    data = read_state(path)

    if data is not None:
        return structure_state(data)

    return []


def read_state(path: pathlib.Path, /) -> bytes | None:
    try:
        data = path.read_bytes()

    except FileNotFoundError:
        _LOG.info("State file not found")
        return None

    except OSError as err:
        _LOG.error("Reading state file failed", exc_info=err)
        return None

    return data


def structure_state(data: bytes, /) -> list[PartialPlayer]:
    try:
        raw_state = orjson.loads(data)

    except orjson.JSONDecodeError as err:
        _LOG.error(msg="Invalid json state", exc_info=err)
        return []

    try:
        partial_state = converter.structure(raw_state, list[PartialPlayer])

    except ClassValidationError as err:
        _LOG.error(msg="Cannot structure state", exc_info=err)
        return []

    else:
        _LOG.info("Restored %d players", len(partial_state))
        return partial_state


# ---------------------------------------------- save ----------------------------------------------


def save_state(path: Pathish, /, state: abc.Iterable[Player]) -> None:
    path = pathlib.Path(path)
    state_path = path / STATE_FILE
    path.mkdir(exist_ok=True)

    move_old_state(from_=state_path, to=path / OLD_STATE_FILE)

    partial_players = [player.as_partial() for player in state]
    _LOG.info("Dumping %d players", len(partial_players))

    try:
        data = converter.unstructure(partial_players)
        bytes_ = orjson.dumps(data)

    except Exception as exc:
        _LOG.error("Failed to dump state", exc_info=exc)
        return

    try:
        state_path.write_bytes(bytes_)

    except OSError as err:
        _LOG.error("Saving state failed", exc_info=err)


def move_old_state(from_: pathlib.Path, to: pathlib.Path) -> bool:
    try:
        from_.replace(to)

    except FileNotFoundError:
        _LOG.warning("Old state not found")

    except OSError as err:
        _LOG.error("Failed to move state", exc_info=err)
        return False

    return True
