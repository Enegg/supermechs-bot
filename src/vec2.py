import math
from typing import ClassVar, Self, SupportsIndex

import attrs

__all__ = ("Point2D",)


# NOTE: no need for __i<>__ methods, see https://docs.python.org/3/reference/datamodel.html#object.__iadd__
@attrs.frozen
class Point2D:
    ZERO: ClassVar[Self]
    x: int = 0
    y: int = 0
    type Rhs = SupportsIndex | Self
    type Lhs = SupportsIndex

    def __add__(self, rhs: Rhs, /) -> Self:
        match rhs:
            case Point2D(x, y):
                return self.__class__(self.x + x, self.y + y)
            case SupportsIndex():
                rhs = int(rhs)
                return self.__class__(self.x + rhs, self.y + rhs)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, rhs: Rhs, /) -> Self:
        match rhs:
            case Point2D(x, y):
                return self.__class__(self.x - x, self.y - y)
            case SupportsIndex():
                rhs = int(rhs)
                return self.__class__(self.x - rhs, self.y - rhs)
        return NotImplemented

    def __rsub__(self, lhs: Lhs, /) -> Self:
        if not isinstance(lhs, SupportsIndex):
            return NotImplemented

        lhs = int(lhs)
        return self.__class__(lhs - self.x, lhs - self.y)

    def __mul__(self, rhs: Rhs, /) -> Self:
        match rhs:
            case Point2D(x, y):
                return self.__class__(self.x * x, self.y * y)
            case SupportsIndex():
                rhs = int(rhs)
                return self.__class__(self.x * rhs, self.y * rhs)
        return NotImplemented

    __rmul__ = __mul__

    def __floordiv__(self, rhs: Rhs, /) -> Self:
        match rhs:
            case Point2D(x, y):
                return self.__class__(self.x // x, self.y // y)
            case SupportsIndex():
                rhs = int(rhs)
                return self.__class__(self.x // rhs, self.y // rhs)
        return NotImplemented

    def __abs__(self) -> int:
        return math.isqrt(self.x * self.x + self.y * self.y)

    def __neg__(self) -> Self:
        return self.__class__(-self.x, -self.y)

    def __complex__(self) -> complex:
        return complex(self.x, self.y)

    def normalize(self) -> Self:
        return self // abs(self)

    def dot(self, rhs: Self, /) -> int:
        return self.x * rhs.x + self.y * rhs.y


Point2D.ZERO = Point2D()
