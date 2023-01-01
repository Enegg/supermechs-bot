from .player_factory import *


def register_injections() -> None:
    import bridges.injectors  # pyright: ignore[reportUnusedImport]
