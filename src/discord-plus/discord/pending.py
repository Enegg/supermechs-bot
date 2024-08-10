"""Backport of pending PRs and/or things eventually to be found in future library releases."""

import importlib
import importlib.util
import pkgutil
from collections import abc

__all__ = ("walk_modules",)


def walk_modules(
    paths: abc.Iterable[str],
    prefix: str = "",
    ignore: abc.Iterable[str] | abc.Callable[[str], bool] | None = None,
) -> abc.Iterator[str]:
    if isinstance(ignore, abc.Iterable):
        ignore_tup = tuple(ignore)
        ignore = lambda path: path.startswith(ignore_tup)  # noqa: E731

    seen: set[str] = set()

    for _, name, ispkg in pkgutil.iter_modules(paths, prefix):
        if ignore is not None and ignore(name):
            continue

        if not ispkg:
            yield name
            continue

        module = importlib.import_module(name)

        if hasattr(module, "setup"):
            yield name
            continue

        sub_paths: list[str] = []

        for path in module.__path__ or ():
            if path not in seen:
                seen.add(path)
                sub_paths.append(path)

        if sub_paths:
            yield from walk_modules(sub_paths, name + ".", ignore)


def find_submodules(root_module: str, package: str | None = None) -> tuple[list[str], str]:
    if (spec := importlib.util.find_spec(root_module, package=package)) is None:
        msg = f"Unable to find root module '{root_module}'"
        raise ImportError(msg, name=root_module)

    if (paths := spec.submodule_search_locations) is None:
        msg = f"Module '{root_module}' is not a package"
        raise ImportError(msg, name=root_module)

    return paths, spec.name
