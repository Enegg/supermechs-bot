import pytest

from app.ui import get_options_slice_for_page


@pytest.mark.parametrize(
    ("count", "index", "expected"),
    [
        (25, 0, (0, 25)),
        (26, 0, (0, 24)),
        (26, 1, (24, 26)),
        (48, 1, (24, 48)),
        (50, 1, (24, 47)),
        (50, 2, (47, 50)),
        (75, 2, (47, 70)),
    ],
)
def test_option_range(count: int, index: int, expected: tuple[int, int]) -> None:
    start, end = get_options_slice_for_page(count, index)
    assert (start, end) == expected
