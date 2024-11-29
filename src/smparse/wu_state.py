from collections import abc
from typing import ClassVar

import attrs
import attrs.validators as v


@attrs.define(kw_only=True)
class MechSetup:
    setup_length: ClassVar[int] = 21

    name: str
    setup: abc.Sequence[int] = attrs.field(
        validator=(v.min_len(setup_length), v.max_len(setup_length))
    )


@attrs.define
class PlayerState:
    mechs: abc.Mapping[str, MechSetup]


