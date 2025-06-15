"""Utilities related to handling bot extensions."""

import importlib.util
import logging
import pkgutil
from collections import abc

__all__ = ("load_extensions",)

_LOG = logging.getLogger("extensions")


def find_submodules(root_module: str, package: str | None = None) -> tuple[abc.Sequence[str], str]:
    if (spec := importlib.util.find_spec(root_module, package=package)) is None:
        msg = f"Unable to find root module '{root_module}'"
        raise ImportError(msg, name=root_module)

    if (paths := spec.submodule_search_locations) is None:
        msg = f"Module '{root_module}' is not a package"
        raise ImportError(msg, name=root_module)

    return paths, spec.name


def walk_extensions(root_module: str, *, package: str | None = None) -> abc.Iterator[str]:
    paths, name = find_submodules(root_module, package=package)

    for _, sub_name, _ in pkgutil.iter_modules(paths, f"{name}."):
        yield sub_name


def load_extensions(
    loader: abc.Callable[[str], None], root_module: str, *, package: str | None = None
) -> None:
    for module_name in walk_extensions(root_module, package=package):
        try:
            loader(module_name)

        except Exception as exc:
            _LOG.exception(f"Ignoring exception in {module_name}:", exc_info=exc)
