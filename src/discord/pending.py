"""Backport of pending PRs and/or things eventually to be found in future library releases."""

import importlib
import importlib.util
import pkgutil
from collections import abc

__all__ = ("find_submodules", "walk_modules")


def walk_modules(
    paths: abc.Iterable[str],
    prefix: str = "",
    ignore: abc.Callable[[str], bool] | None = None,
) -> abc.Iterator[str]:
    for _, name, _ in pkgutil.iter_modules(paths, prefix):
        if ignore is not None and ignore(name):
            continue

        yield name


def find_submodules(root_module: str, package: str | None = None) -> tuple[abc.Sequence[str], str]:
    if (spec := importlib.util.find_spec(root_module, package=package)) is None:
        msg = f"Unable to find root module '{root_module}'"
        raise ImportError(msg, name=root_module)

    if (paths := spec.submodule_search_locations) is None:
        msg = f"Module '{root_module}' is not a package"
        raise ImportError(msg, name=root_module)

    return paths, spec.name
