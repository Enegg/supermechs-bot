from collections import abc


def search_for(
    phrase: str, strings: abc.Iterable[str], *, ignore_case: bool = True
) -> abc.Iterator[str]:
    """Finds strings matching a phrase.

    It is considered a match if for every word in the phrase there is a word
    in a string that begins with it and it appears after all previous matches.
    For example, `burn sco` would match both `half burnt scope` & `burn half scope`, but
    `burn half` would match only the latter.

    Parameters
    ----------
    phrase:
        String of whitespace-separated words.
    strings:
        Iterable of strings to match against.
    ignore_case:
        Whether the search should be case sensitive.
    """
    case = str.lower if ignore_case else str
    parts = case(phrase).split()

    for string in strings:
        words = iter(case(string).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield string


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
        # don't bother with single capital letters
        return None
    # filter out already-acronym names, like "EMP"
    if name.isupper():
        return None
    # names which are partially acronyms are fine
    return "".join(filter(str.isupper, name)).lower()
