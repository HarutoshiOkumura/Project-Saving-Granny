"""Wear time: was the camera on and moving, minute by minute (docs/INSIGHTS.md design 1).

Every frame the worker receives counts, before any filter drops it. A frame "moved" unless it is
a near-duplicate of the last kept frame: a phone lying on a table sends near-duplicates, a worn
one does not (a blurry frame counts as moving: walking smears). Counts only: no room, no item, no
image, so a frame from a no-capture room counts toward wear without saying where it was.

Pure and clock-free: the worker adds frames and takes the minutes that changed since the last
take, then stores them with one upsert. Each minute keeps its running total for KEEP after the
newest frame, so a minute stored while still filling is overwritten later with its full count.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.perception.filters import FilterVerdict

KEEP = timedelta(minutes=15)


@dataclass(frozen=True)
class WearCount:
    device_id: str
    minute: datetime  # UTC, whole minute
    frames: int
    moving: int


def moved(verdict: FilterVerdict, duplicate_cut: float) -> bool:
    """Not a near-duplicate of the last kept frame. Blurry frames are not compared, and count."""
    if verdict.result == "blurry" or verdict.similarity is None:
        return True
    return verdict.similarity < duplicate_cut


class WearCounter:
    def __init__(self) -> None:
        self._counts: dict[tuple[str, datetime], list[int]] = {}
        self._changed: set[tuple[str, datetime]] = set()
        self._newest: datetime | None = None

    def add(self, device_id: str, captured_at: datetime, moving: bool) -> None:
        minute = captured_at.astimezone(UTC).replace(second=0, microsecond=0)
        count = self._counts.setdefault((device_id, minute), [0, 0])
        count[0] += 1
        count[1] += int(moving)
        self._changed.add((device_id, minute))
        if self._newest is None or minute > self._newest:
            self._newest = minute

    def take(self) -> list[WearCount]:
        """The minutes that changed since the last take, oldest first; forgets old minutes."""
        out = [WearCount(d, m, *self._counts[(d, m)]) for d, m in sorted(self._changed)]
        self._changed.clear()
        if self._newest is not None:
            old = [key for key in self._counts if key[1] < self._newest - KEEP]
            for key in old:
                del self._counts[key]
        return out

    def give_back(self, counts: list[WearCount]) -> None:
        """A store that failed: send these minutes again next time, if still remembered."""
        for c in counts:
            if (c.device_id, c.minute) in self._counts:
                self._changed.add((c.device_id, c.minute))
