import statistics
import typing as t

from typeshed import KT, VT, twotuple

from SuperMechs.api import STATS, AnyStats, Element, Stat, ValueRange
from SuperMechs.core import Names

Entry = tuple[t.Any, ...]


custom_stats: dict[str, Stat] = {
    "spread": Stat("spread", Names("Damage spread"), "🎲", False),
    "anyDmg": Stat("anyDmg", Names("Damage"), Element.COMBINED.emoji),
    "totalDmg": Stat("totalDmg", Names("Damage potential"), "🎯"),
}
STAT_KEY_ORDER = tuple(STATS)


class ComparisonContext(t.NamedTuple):
    coerce_damage_types: bool = False
    damage_average: bool = False
    damage_spread: bool = False
    damage_potential: bool = False


def sum_damage_entries(
    entries: t.Iterable[tuple[ValueRange | None, ...]], size: int
) -> tuple[ValueRange | None, ...]:
    entry_values: list[ValueRange | None] = [None] * size

    for entry in entries:
        for i, value in enumerate(entry):
            if value is None:
                continue
            # somehow, entry_values[i] is None doesn't narrow type on following item access
            # so need to reassign the value manually
            current_value = entry_values[i]

            if current_value is None:
                current_value = value

            else:
                current_value += value

            entry_values[i] = current_value

    return tuple(entry_values)


damage_keys = frozenset(("phyDmg", "expDmg", "eleDmg", "anyDmg"))


class EntryConverter:
    """Class responsible for merging a set of mappings and ."""

    size: int
    """The number of side to side entries to compare."""
    key_order: list[str]
    """The order in which final keys should appear."""
    entries: dict[str, Entry]
    """Current set of entries."""

    def __init__(self, *stat_mappings: AnyStats, key_order: t.Sequence[str]) -> None:
        if len(stat_mappings) < 2:
            raise ValueError("Need at least two mappings to compare")

        self.size = len(stat_mappings)
        self.key_order = sorted(
            set[str]().union(*map(AnyStats.keys, stat_mappings)), key=key_order.index
        )
        self.entries = {
            key: tuple(mapping.get(key) for mapping in stat_mappings) for key in self.key_order
        }

    def __str__(self) -> str:
        return "\n".join(f"{key}: {value}" for key, value in self)

    def __repr__(self) -> str:
        return f"<Comparator {self.key_order} {self.entries}>"

    def __iter__(self) -> t.Iterator[tuple[str, Entry]]:
        for key in self.key_order:
            yield key, self.entries[key]

    def coerce_damage_entries(self) -> None:
        present_damage_keys = self.entries.keys() & damage_keys

        if not present_damage_keys:
            return

        # don't add one since the entry will be gone at the time of insert
        index = min(map(self.key_order.index, present_damage_keys))
        entry = sum_damage_entries(map(self.remove_entry, present_damage_keys), self.size)
        self.insert_entry("anyDmg", index, entry)

    def insert_damage_spread_entry(self) -> None:
        present_damage_keys = self.entries.keys() & damage_keys

        if not present_damage_keys:
            return

        total_damage = sum_damage_entries(
            map(self.entries.__getitem__, present_damage_keys), self.size
        )

        # insert after the last damage entry
        index = max(map(self.key_order.index, present_damage_keys)) + 1

        self.insert_entry(
            "spread",
            index,
            tuple(None if value is None else statistics.pstdev(value) for value in total_damage),
        )

    def insert_entry(self, key: str, index: int, entry: Entry) -> None:
        """Insert given key: entry pair at given index."""
        self.key_order.insert(index, key)
        self.entries[key] = entry

    def insert_after(self, key: str, after: str, entry: Entry) -> int:
        """Insert 'key' after another key. Returns the index it inserted at."""
        index = self.key_order.index(after) + 1
        self.insert_entry(key, index, entry)
        return index

    def remove_entry(self, key: str) -> Entry:
        """Remove and return an existing entry."""
        self.key_order.remove(key)
        return self.entries.pop(key)

    def run_conversions(self, ctx: ComparisonContext) -> None:
        if ctx.coerce_damage_types:
            self.coerce_damage_entries()

        if ctx.damage_spread:
            self.insert_damage_spread_entry()

        if ctx.damage_average:
            pass
