import statistics
import typing as t

from SuperMechs.api import AnyStats, ValueRange

if t.TYPE_CHECKING:
    from .stat_comparator import ComparisonContext

__all__ = ("EntryConverter",)

Entry = tuple[t.Any, ...]


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
    """Class responsible for merging a set of mappings and running conversions."""

    key_order: list[str]
    """The order in which final keys should appear."""
    entries: dict[str, Entry]
    """Current set of entries."""
    _entry_size: int

    @property
    def entry_size(self) -> int:
        """The number of side to side entries to compare."""
        return self._entry_size

    def __init__(self, *stat_mappings: AnyStats, key_order: t.Sequence[str]) -> None:
        if len(stat_mappings) < 2:
            raise ValueError("Need at least two mappings to compare")

        self._entry_size = len(stat_mappings)
        self.key_order = sorted(
            set[str]().union(*map(AnyStats.keys, stat_mappings)), key=key_order.index
        )
        self.entries = {
            key: tuple(mapping.get(key) for mapping in stat_mappings) for key in self.key_order
        }

    def __str__(self) -> str:
        return "\n".join(f"{key}: {value}" for key, value in self)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.key_order} {self.entries}>"

    def __iter__(self) -> t.Iterator[tuple[str, Entry]]:
        for key in self.key_order:
            yield key, self.entries[key]

    def get_entry(self, key: str) -> Entry:
        """Return the entry at given key."""
        return self.entries[key]

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

    def coerce_damage_entries(self) -> None:
        present_damage_keys = self.entries.keys() & damage_keys

        if not present_damage_keys:
            return

        # don't add one since the entry will be gone at the time of insert
        index = min(map(self.key_order.index, present_damage_keys))
        entry = sum_damage_entries(map(self.remove_entry, present_damage_keys), self.entry_size)
        self.insert_entry("anyDmg", index, entry)

    def insert_damage_spread_entry(self) -> None:
        present_damage_keys = self.entries.keys() & damage_keys

        if not present_damage_keys:
            return

        # insert after the last damage entry
        index = max(map(self.key_order.index, present_damage_keys)) + 1
        total_damage = sum_damage_entries(map(self.get_entry, present_damage_keys), self.entry_size)

        self.insert_entry(
            "spread",
            index,
            tuple(None if value is None else statistics.pstdev(value) for value in total_damage),
        )

    def run_conversions(self, ctx: ComparisonContext) -> None:
        if ctx.coerce_damage_types:
            self.coerce_damage_entries()

        if ctx.damage_spread:
            self.insert_damage_spread_entry()
