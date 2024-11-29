import math
from typing import ClassVar, Self, SupportsFloat

import attrs

__all__ = ("Point2D",)


# NOTE: no need for __i<>__ methods, see https://docs.python.org/3/reference/datamodel.html#object.__iadd__
@attrs.frozen
class Point2D:
    ZERO: ClassVar[Self]
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: SupportsFloat | Self, /) -> Self:
        match other:
            case SupportsFloat():
                other = float(other)
                return type(self)(self.x + other, self.y + other)
            case Point2D(x, y):
                return type(self)(self.x + x, self.y + y)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other: SupportsFloat | Self, /) -> Self:
        match other:
            case SupportsFloat():
                other = float(other)
                return type(self)(self.x - other, self.y - other)
            case Point2D(x, y):
                return type(self)(self.x - x, self.y - y)
        return NotImplemented

    def __mul__(self, other: SupportsFloat | Self, /) -> Self:
        match other:
            case SupportsFloat():
                other = float(other)
                return type(self)(self.x * other, self.y * other)
            case Point2D(x, y):
                return type(self)(self.x * x, self.y * y)
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, other: SupportsFloat | Self, /) -> Self:
        match other:
            case SupportsFloat():
                other = float(other)
                return type(self)(self.x / other, self.y / other)
            case Point2D(x, y):
                return type(self)(self.x / x, self.y / y)
        return NotImplemented

    def __abs__(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def __neg__(self) -> Self:
        return type(self)(-self.x, -self.y)

    def __complex__(self) -> complex:
        return complex(self.x, self.y)

    def normalize(self) -> Self:
        return self / abs(self)

    def dot(self, other: Self) -> float:
        return self.x * other.x + self.y * other.y


Point2D.ZERO = Point2D()
