"""
Utilities related to handling bot extensions.
"""
import importlib.util
import os.path
import typing as t

from .pending import walk_modules

__all__ = ("load_extensions",)

LoadCallback: t.TypeAlias = t.Callable[[str], None]


def load_extensions(
    loader: LoadCallback,
    root_module: str,
    *,
    package: str | None = None,
    ignore: t.Iterable[str] | t.Callable[[str], bool] | None = None,
) -> None:
    if "/" in root_module or "\\" in root_module:
        path = os.path.relpath(root_module)
        if ".." in path:
            msg = "Paths outside the cwd are not supported. Try using the module name instead."
            raise ImportError(msg, path=path)
        root_module = path.replace(os.sep, ".")

    root_module = importlib.util.resolve_name(root_module, package)

    if (spec := importlib.util.find_spec(root_module)) is None:
        msg = f"Unable to find root module '{root_module}'"
        raise ImportError(msg, name=root_module)

    if (paths := spec.submodule_search_locations) is None:
        msg = f"Module '{root_module}' is not a package"
        raise ImportError(msg, name=root_module)

    for module_name in walk_modules(paths, f"{spec.name}.", ignore):
        loader(module_name)
