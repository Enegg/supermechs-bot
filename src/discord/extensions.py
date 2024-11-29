"""Utilities related to handling bot extensions."""

import logging
import sys
from collections import abc

from .pending import find_submodules, walk_modules

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

__all__ = ("load_extensions",)

_LOG = logging.getLogger("extensions")


def walk_extensions(
    root_module: str,
    *,
    package: str | None = None,
    ignore: abc.Callable[[str], bool] | None = None,
) -> abc.Iterator[str]:
    paths, name = find_submodules(root_module, package=package)
    yield from walk_modules(paths, f"{name}.", ignore)


def _load_extensions(loader: abc.Callable[[str], None], plugins: abc.Iterable[str]) -> None:
    problems: list[Exception] = []

    for module_name in plugins:
        try:
            loader(module_name)

        except Exception as exc:
            problems.append(exc)

    if problems:
        # TODO: exceptions are raised at walk_modules' import_module
        msg = "Exceptions during loading:"
        exc = ExceptionGroup(msg, problems)

        if __debug__:
            _LOG.exception("Ignoring exceptions:", exc_info=exc)

        else:
            raise exc


def load_extensions(
    loader: abc.Callable[[str], None],
    root_module: str,
    *,
    package: str | None = None,
    ignore: abc.Callable[[str], bool] | None = None,
) -> None:
    _load_extensions(loader, walk_extensions(root_module, package=package, ignore=ignore))
