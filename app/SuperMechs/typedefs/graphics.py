import typing as t

__all__ = (
    "RawPoint2D",
    "RawTorsoAttachments",
    "AnyRawAttachment",
    "Rectangle",
    "ItemImageParams",
)


class RawPoint2D(t.TypedDict):
    x: int
    y: int


RawTorsoAttachments = dict[str, RawPoint2D]
AnyRawAttachment = RawPoint2D | RawTorsoAttachments | None


class Rectangle(RawPoint2D):
    width: int
    height: int


class ItemImageParams(t.TypedDict, total=False):
    width: int
    height: int
    attachment: RawPoint2D | RawTorsoAttachments
