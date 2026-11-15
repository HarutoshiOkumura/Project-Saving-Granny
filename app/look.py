"""Where to look: places ranked with chances, for when Save It is not sure (D33, the judge's ask).

Pure: `find_item`'s answer plus the home's habits and glimpses in, ranked places out. No database,
no model, no clock (the caller passes `now`).

Each place with a clue gets a score; a place's chance is its share of all scores plus a constant
"somewhere else", so one weak clue never reads as 100%.

    last seen   8 if confident, else 3; halves every 24 h, never below a quarter    the newest stay
    glimpse     3 each; halves every 2 h        a one-frame stay newer than the answer (any, if
                                                never seen); one frame is a hint, never an answer
    usual       3 x stays here / (n + 2)        n = settled stays anywhere, so a short history
                                                is weak and a long one tends to its share
    home        1.5 at the place the family says it belongs
    carried     x 1.5 for places in the room the wearer went to after holding it
    elsewhere   1, the places it has never been seen

A place the answer has just ruled out (seen empty three times) keeps only a newer glimpse.
The band uses 0003 `rank_item`'s cut-offs: high when the top place has at least 60% and leads the
second by 25 points, split when the top two have 60% together, low otherwise.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.memory.schema import FindResult, Item, LookEvidence, Place, PlaceName

Why = Literal["last_seen", "glimpse", "usual", "home"]
Band = Literal["high", "split", "low"]

LAST_SEEN = 8.0
LAST_SEEN_UNSURE = 3.0
LAST_SEEN_HALF_LIFE_H = 24.0
LAST_SEEN_FLOOR = 0.25
GLIMPSE = 3.0
GLIMPSE_HALF_LIFE_H = 2.0
USUAL = 3.0
USUAL_PRIOR_STAYS = 2
HOME = 1.5
CARRIED_ROOM = 1.5
ELSEWHERE = 1.0
MAX_PLACES = 4
MIN_SHARE = 0.03  # a place under 3% goes into "somewhere else"
USUAL_MIN_STAYS = 2  # a habit needs two settled stays at one place, as in find_item's `usual`


class LookPlace(BaseModel):
    """One place to look, most likely first. `room` and `landmark` are the spoken words."""

    model_config = ConfigDict(frozen=True)

    landmark_id: UUID
    room: str
    landmark: str
    address: str
    pct: int
    why: list[Why]
    minutes_ago: int | None = None  # the newest clue at this place


class WhereToLook(BaseModel):
    """Ranked places for one item. `places` pcts plus `elsewhere_pct` add up to 100."""

    model_config = ConfigDict(frozen=True)

    band: Band
    places: list[LookPlace]
    elsewhere_pct: int
    ruled_out: Place | None = None  # seen empty just now: never offered again for this answer


class _Clues:
    def __init__(self, place: PlaceName) -> None:
        self.place = place
        self.score = 0.0
        self.why: list[Why] = []
        self.newest: datetime | None = None

    def add(self, score: float, why: Why | None, at: datetime | None) -> None:
        self.score += score
        if why is not None and why not in self.why:
            self.why.append(why)
        if at is not None and (self.newest is None or at > self.newest):
            self.newest = at


def where_to_look(
    item: Item, result: FindResult | None, evidence: LookEvidence, now: datetime
) -> WhereToLook | None:
    """None when there is no item to rank (no answer, or an unknown item)."""
    if result is None or result.state == "unknown_item":
        return None
    places = {p.landmark_id: p for p in evidence.places}
    by_address = {p.address: p.landmark_id for p in evidence.places}
    clues: dict[UUID, _Clues] = {}

    def at(landmark_id: UUID | None) -> _Clues | None:
        if landmark_id is None or landmark_id not in places:
            return None
        return clues.setdefault(landmark_id, _Clues(places[landmark_id]))

    belief = by_address.get(result.address) if result.address else None
    ruled_out = belief if result.state == "not_there_anymore" else None
    answered_at = result.last_seen_at if result.state != "never_seen" else None

    if result.state == "seen" and (c := at(belief)) and result.last_seen_at:
        weight = LAST_SEEN if result.confident else LAST_SEEN_UNSURE
        decay = max(LAST_SEEN_FLOOR, _halves(now, result.last_seen_at, LAST_SEEN_HALF_LIFE_H))
        c.add(weight * decay, "last_seen", result.last_seen_at)

    for g in evidence.glimpses:
        if g.item_id != item.id or (answered_at and g.last_seen_at <= answered_at):
            continue
        if c := at(g.landmark_id):
            weight = GLIMPSE * _halves(now, g.last_seen_at, GLIMPSE_HALF_LIFE_H)
            c.add(weight, "glimpse", g.last_seen_at)

    habits = [u for u in evidence.usual if u.item_id == item.id and u.landmark_id != ruled_out]
    stays = sum(u.episodes for u in habits)
    for u in habits:
        if c := at(u.landmark_id):
            weight = USUAL * u.episodes / (stays + USUAL_PRIOR_STAYS)
            c.add(weight, "usual" if u.episodes >= USUAL_MIN_STAYS else None, u.last_seen_at)

    if item.home_landmark_id != ruled_out and (c := at(item.home_landmark_id)):
        c.add(HOME, "home", None)

    if result.state == "carried" and (went := result.wearer_went_to or result.room):
        for c in clues.values():
            if c.place.room_spoken == went:
                c.score *= CARRIED_ROOM

    ranked = sorted(
        (c for c in clues.values() if c.score > 0),
        key=lambda c: (-c.score, c.place.landmark_spoken),
    )
    total = ELSEWHERE + sum(c.score for c in ranked)
    kept = [c for c in ranked if c.score / total >= MIN_SHARE][:MAX_PLACES]
    elsewhere = total - sum(c.score for c in kept)
    pcts = _percentages([c.score for c in kept] + [elsewhere])

    out = [
        LookPlace(
            landmark_id=c.place.landmark_id,
            room=c.place.room_spoken,
            landmark=c.place.landmark_spoken,
            address=c.place.address,
            pct=pct,
            why=c.why,
            minutes_ago=_minutes(now, c.newest),
        )
        for c, pct in zip(kept, pcts, strict=False)
    ]
    gone = places.get(ruled_out) if ruled_out else None
    return WhereToLook(
        band=_band([p.pct for p in out]),
        places=out,
        elsewhere_pct=pcts[-1],
        ruled_out=Place(room=gone.room_spoken, landmark=gone.landmark_spoken) if gone else None,
    )


def _halves(now: datetime, then: datetime, half_life_h: float) -> float:
    age_h = max(0.0, (now - then).total_seconds() / 3600)
    return 0.5 ** (age_h / half_life_h)


def _minutes(now: datetime, then: datetime | None) -> int | None:
    return None if then is None else max(0, round((now - then).total_seconds() / 60))


def _percentages(scores: list[float]) -> list[int]:
    """Whole percentages that add up to exactly 100 (largest remainder first)."""
    total = sum(scores)
    exact = [100 * s / total for s in scores]
    pcts = [int(e) for e in exact]
    by_remainder = sorted(range(len(exact)), key=lambda i: pcts[i] - exact[i])
    for i in by_remainder[: 100 - sum(pcts)]:
        pcts[i] += 1
    return pcts


def _band(pcts: list[int]) -> Band:
    first = pcts[0] if pcts else 0
    second = pcts[1] if len(pcts) > 1 else 0
    if first >= 60 and first - second >= 25:
        return "high"
    if first + second >= 60:
        return "split"
    return "low"
