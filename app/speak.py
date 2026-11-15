"""find_item JSON -> one spoken sentence. Pure: no I/O, no clock; `now` is passed in.

Follows `.claude/rules/voice.md` exactly. Change the wording there first (D14), then here.
Where the rules are silent:
- `usual` has no relation, so it is always "on" its landmark, as in the rule's template.
- A missing `confident` counts as not confident ("I think"), to stay honest.
- 58 and 59 minutes say "about fifty-five minutes ago", to stay inside the 10 to 59 band.
- Anything a template needs that is missing gives the fallback sentence.
"""

import math
import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.memory.schema import FindResult, Place

FALLBACK = "I'm not sure right now."
UNKNOWN_ITEM = "I'm sorry, which thing are you looking for?"
UNKNOWN_NAMED = "I don't know your {thing} yet, but your family can teach me."
# Dropped from `heard` before naming it back ("where is my wallet" -> "wallet"). One or two words
# left are the thing; anything else means we did not catch it, so ask. Keep in step with
# FILLER in agent/saveit.mjs.
FILLER_WORDS = frozenset(
    "where wheres where's is are my the did i put find lost please can you help me have seen your "
    "a an to look for looking it that this thing things something stuff um uh er hmm".split()
)

RELATION_WORDS = {"on": "on", "in": "in", "under": "under", "next_to": "next to"}
UNKNOWN_RELATION = "near"

NUMBER_WORDS = {
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    10: "ten",
    15: "fifteen",
    20: "twenty",
    25: "twenty-five",
    30: "thirty",
    35: "thirty-five",
    40: "forty",
    45: "forty-five",
    50: "fifty",
    55: "fifty-five",
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def speak(result: FindResult, now: datetime) -> str:
    """The one sentence the caller hears. `now` must be timezone-aware."""
    match result.state:
        case "unknown_item":
            sentence = _unknown(result)
        case "never_seen":
            sentence = _never_seen(result)
        case "seen":
            sentence = _seen(result, now)
        case "carried":
            sentence = _carried(result, now)
        case "not_there_anymore":
            sentence = _not_there_anymore(result)
    return _capitalize(sentence) if sentence else FALLBACK


# ---------- one template per state ----------


def _unknown(result: FindResult) -> str:
    """Name the thing back when we caught it clearly, so the caller knows they were heard."""
    heard = (result.heard or "").lower()
    words = [w for w in re.findall(r"[a-z']+", heard) if w not in FILLER_WORDS]
    return UNKNOWN_NAMED.format(thing=" ".join(words)) if 1 <= len(words) <= 2 else UNKNOWN_ITEM


def _seen(r: FindResult, now: datetime) -> str | None:
    where = _where(r.landmark, r.room, r.relation)
    when = _when(r.last_seen_at, r.timezone, now)
    if not (r.item and where and when):
        return None
    opener = "I think I saw" if _hedge(r) else "I last saw"
    return f"{opener} your {r.item} {where} {when}."


def _carried(r: FindResult, now: datetime) -> str | None:
    when = _when(r.last_seen_at, r.timezone, now)
    if not (r.item and when):
        return None
    sentence = f"you had your {r.item} in your hand"
    if r.room:
        sentence += f" in {r.room}"
    sentence += f" {when}"
    if r.wearer_went_to and not _same(r.wearer_went_to, r.room):
        sentence += f", and then you went to {r.wearer_went_to}"
    return _maybe_hedge(r, sentence + ".")


def _not_there_anymore(r: FindResult) -> str | None:
    where = _where(r.landmark, r.room, r.relation)
    if not (r.item and where) or r.plural is None:
        return None
    is_not = "aren't" if r.plural else "isn't"
    sentence = f"your {r.item} {is_not} {where} anymore"
    usual = _usual(r.usual, ruled_out_room=r.room, ruled_out_landmark=r.landmark)
    if usual:
        sentence += f", but {_lives(r.plural)} {usual}"
    else:
        pronoun = "they" if r.plural else "it"
        sentence += f", and I haven't seen where {pronoun} went"
    return _maybe_hedge(r, sentence + ".")


def _never_seen(r: FindResult) -> str | None:
    if not r.item or r.plural is None:
        return None
    usual = _usual(r.usual)
    if usual:
        return f"I haven't seen your {r.item} yet, but {_lives(r.plural)} {usual}."
    return f"I haven't seen your {r.item} yet."


# ---------- pieces ----------


def _where(landmark: str | None, room: str | None, relation: str | None) -> str | None:
    """'on the kitchen counter', or 'in the kitchen' when there is no landmark."""
    if landmark:
        return f"{RELATION_WORDS.get(relation or '', UNKNOWN_RELATION)} {landmark}"
    if room:
        return f"in {room}"
    return None


def _usual(
    usual: Place | None,
    ruled_out_room: str | None = None,
    ruled_out_landmark: str | None = None,
) -> str | None:
    """Where the item usually lives, or None. Never the place the answer has just ruled out."""
    if usual is None:
        return None
    if usual.landmark:
        if ruled_out_landmark and _same(usual.landmark, ruled_out_landmark):
            return None
        if not ruled_out_landmark and ruled_out_room and _same(usual.room, ruled_out_room):
            return None
        return f"on {usual.landmark}"
    if usual.room and not _same(usual.room, ruled_out_room):
        return f"in {usual.room}"
    return None


def _when(seen_at: datetime | None, timezone: str | None, now: datetime) -> str | None:
    """The time words table in the voice rules."""
    if seen_at is None:
        return None
    minutes = math.floor((now - seen_at).total_seconds() / 60)
    if minutes < 2:
        return "just now"
    if minutes < 10:
        return "a few minutes ago"
    if minutes < 60:
        return f"about {NUMBER_WORDS[min(_round_half_up(minutes / 5) * 5, 55)]} minutes ago"
    if minutes < 90:
        return "about an hour ago"
    if minutes <= 5 * 60:
        return f"about {NUMBER_WORDS[_round_half_up(minutes / 60)]} hours ago"
    if timezone is None:
        return None
    zone = ZoneInfo(timezone)
    seen_local = seen_at.astimezone(zone)
    days = (now.astimezone(zone).date() - seen_local.date()).days
    if days == 0:
        return f"this {_part_of_day(seen_local)}"
    if days == 1:
        return f"yesterday {_part_of_day(seen_local)}"
    if days <= 6:
        return f"on {WEEKDAYS[seen_local.weekday()]}"
    return "a while ago"


def _part_of_day(local: datetime) -> str:
    clock = local.time()
    if clock < time(12):
        return "morning"
    if clock <= time(17):
        return "afternoon"
    return "evening"


def _hedge(r: FindResult) -> bool:
    return r.confident is not True or r.possible_newer_glimpse is True


def _maybe_hedge(r: FindResult, sentence: str) -> str:
    return f"I think {sentence}" if _hedge(r) else sentence


def _lives(plural: bool) -> str:
    return "they usually live" if plural else "it usually lives"


def _same(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and a.strip().casefold() == b.strip().casefold()


def _round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def _capitalize(sentence: str) -> str:
    return sentence[:1].upper() + sentence[1:]
