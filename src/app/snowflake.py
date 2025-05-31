# https://discord.com/developers/docs/reference#snowflakes
# https://github.com/twitter-archive/snowflake

import os
import time
from typing import ClassVar, Final, NewType

__all__ = ("APP_EPOCH_MS", "NIL", "Snowflake", "new")

# Snowflake structure:
# 42 bits - timestamp, 10 bits - randomness, 12 bits - counter

Snowflake = NewType("Snowflake", int)

NIL: Final = Snowflake(0)
APP_EPOCH_MS: Final = 1_735_689_600_000  # 1st second of 2025

_TIMESTAMP_BITS: Final = 42
_RANDOM_BITS: Final = 10
_SEQUENCE_BITS: Final = 12
_SEQUENCE_MASK: Final = -1 ^ (-1 << _SEQUENCE_BITS)

_TIMESTAMP_SHIFT: Final = _RANDOM_BITS + _SEQUENCE_BITS
_RANDOM_SHIFT: Final = _SEQUENCE_BITS


class new[SnowflakeT: Snowflake = Snowflake]:  # noqa: N801
    __slots__ = ()

    _sequence: ClassVar[int] = 0
    _last_timestamp: ClassVar[int] = 0

    def __new__(cls) -> SnowflakeT:
        timestamp = cls._get_time_ms()

        if timestamp < cls._last_timestamp:
            msg = f"Time is moving backwards; waiting {cls._last_timestamp - timestamp}ms"
            raise RuntimeWarning(msg)

        if timestamp == cls._last_timestamp:
            cls._sequence = (cls._sequence + 1) & _SEQUENCE_MASK

            if cls._sequence == 0:
                timestamp = cls._wait_until_next_ms()

        else:
            cls._sequence = 0

        cls._last_timestamp = timestamp
        return (
            ((timestamp - APP_EPOCH_MS) << _TIMESTAMP_SHIFT)
            | (cls._random_bits(_RANDOM_BITS) << _RANDOM_SHIFT)
            | cls._sequence
        )  # pyright: ignore[reportReturnType] # fmt: skip

    @classmethod
    def _wait_until_next_ms(cls) -> int:
        timestamp = cls._get_time_ms()

        while timestamp <= cls._last_timestamp:
            timestamp = cls._get_time_ms()

        return timestamp

    @staticmethod
    def _get_time_ms() -> int:
        # NOTE: my device has 1/64s resolution, which isn't quite 1ms
        return int(time.time() * 1000)

    @staticmethod
    def _random_bits(n: int, /) -> int:
        return int.from_bytes(os.urandom(-(-n // 8)), signed=False) & (-1 ^ (-1 << n))
