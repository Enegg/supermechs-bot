import typing as t

from attrs import define

if t.TYPE_CHECKING:
    from supermechs.api import ItemPack
    from supermechs.rendering import PackRenderer

__all__ = ("AppContext",)


@define
class AppContext:
    default_pack: "ItemPack"
    default_renderer: "PackRenderer"
