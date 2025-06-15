from discord import ComponentLimits

__all__ = ("option_to_page_count",)


def option_to_page_count(options: int, /) -> int:
    if options <= ComponentLimits.select_options:
        return 1

    first_and_last_page = (ComponentLimits.select_options - 1) * 2

    if options <= first_and_last_page:
        # fits on two pages, add one of up/down option on each
        return 2

    size = ComponentLimits.select_options - 2
    return 2 + (options - first_and_last_page + size - 1) // size
