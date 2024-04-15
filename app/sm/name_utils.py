from collections import abc


def search_for(
    phrase: str, iterable: abc.Iterable[str], *, case_sensitive: bool = False
) -> abc.Iterator[str]:
    """
    Helper func capable of finding a specific string(s) in iterable.
    It is considered a match if every word in phrase appears in the name
    and in the same order. For example, both `burn scop` & `half scop`
    would match name `Half Burn Scope`, but not `burn half scop`.

    Parameters
    ----------
    phrase:
        String of whitespace-separated words.
    iterable:
        Iterable of strings to match against.
    case_sensitive:
        Whether the search should be case sensitive.
    """
    parts = (phrase if case_sensitive else phrase.lower()).split()

    for name in iterable:
        words = iter((name if case_sensitive else name.lower()).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield name


# the urge to name this function in pascal case
def is_pascal(string: str, /) -> bool:
    """Returns True if the string is pascal-cased, False otherwise.

    A string is pascal-cased if it contains no whitespace, begins with an uppercase letter,
    and all following uppercase letters are separated by at least a single lowercase letter.
        >>> is_pascal("fooBar")
        False
        >>> is_pascal("FooBar")
        True
        >>> is_pascal("Foo Bar")
        False
    """
    # use not .isupper() to have it True on whitespace too
    if not string[:1].isupper():
        return False

    prev_is_upper = False

    for char in string:
        if char.isspace():
            return False

        if prev_is_upper and char.isupper():
            return False

        prev_is_upper = char.isupper()

    return True


def acronym_of(name: str, /) -> str | None:
    """Returns an acronym of the name, or None if one cannot (shouldn't) be made.

    The acronym consists of capital letters in item's name;
    it will not be made for non-PascalCase single-word names, or names which themselves
    are an acronym for something (like EMP).
    """
    if is_pascal(name) and name[1:].islower():
        # cannot make an acronym from a single capital letter
        return None
    # filter out already-acronym names, like "EMP"
    if name.isupper():
        return None
    # Overloaded EMP is fine to make an abbreviation for though
    return "".join(filter(str.isupper, name)).lower()
