import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / "app"))

from app.SuperMechs.ext.stat_comparison import (
    STAT_KEY_ORDER,
    Comparator,
    ComparisonContext,
)

from abstract.files import File

from SuperMechs.api import Item


async def main():
    item1 = Item.from_json(
        await File("tests/data/example_item_v2.json").json(), "@Darkstare", False
    )
    # next(File("tests/data/example_item_v2.json").json().__await__())
    item2 = Item.from_json(await File("tests/data/incomplete_item_v3.json").json(), "@Eneg", False)

    comparator = Comparator(item1.max_stats, item2.max_stats, key_order=STAT_KEY_ORDER)
    context = ComparisonContext()

    breakpoint()
    del context, comparator


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
