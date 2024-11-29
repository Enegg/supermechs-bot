from collections import abc
from typing import Any

from .models import PackBase
from .restructuring import ItemDict, restructure
from .structuring import structure_raw

__all__ = ("structure_pack",)


def structure_pack(data: abc.Mapping[str, Any], /) -> tuple[PackBase, ItemDict]:
    raw = structure_raw(data)
    return restructure(raw)
