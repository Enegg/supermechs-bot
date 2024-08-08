import inspect
from collections import abc


def default_key(*args: abc.Hashable, **kwargs: abc.Hashable) -> abc.Hashable:
    """Compute a key by combining args and kwargs into a tuple.
    Requires all members to be hashable.
    """
    if not kwargs:
        return args

    args_list = list(args)

    for key_val_tuple in kwargs.items():
        args_list += key_val_tuple

    return tuple(args_list)


def callable_repr(func: abc.Callable[..., object], /) -> str:
    """Return the signature of a callable."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"
