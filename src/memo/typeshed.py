from collections import abc
from typing import ParamSpec
from typing_extensions import TypeVar

KT = TypeVar("KT", bound=abc.Hashable, infer_variance=True)
"""Key-type of a mapping."""
VT = TypeVar("VT", infer_variance=True)
"""Value-type of a mapping."""
P = ParamSpec("P")
"""Parameter specification of a callable."""
