"""
Smart matching engine.

Scores a LOST report against a FOUND report from 0..1 using four signals:
  40%  text similarity   (title overlap weighted above description overlap)
  25%  same category
  20%  location similarity
  15%  date proximity    (within MATCH_DATE_WINDOW_DAYS)
"""
import re
from difflib import SequenceMatcher
from config import Config
from database.models import db, Item, MatchRecord
from services.notifications import notify

STOP = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "with", "my", "is",
    "it", "its", "was", "has", "have", "i", "me", "near", "found", "lost", "this", "that",
    "from", "by", "very", "some", "small", "big", "color", "colour",
}


def tokens(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in STOP and len(w) > 1}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap(a, b):
    """Overlap coefficient: forgiving when one side is much shorter."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def score_pair(lost: Item, found: Item) -> float:
    title_sim = _overlap(tokens(lost.title), tokens(found.title))
    desc_sim = jaccard(tokens(lost.title + " " + lost.description),
                       tokens(found.title + " " + found.description))
    text = min(1.0, 0.65 * title_sim + 0.35 * min(1.0, desc_sim * 2))
    cat = 1.0 if lost.category == found.category else 0.0
    loc = SequenceMatcher(None, (lost.location or "").lower(), (found.location or "").lower()).ratio()
    if lost.date_event and found.date_event:
        days = abs((lost.date_event - found.date_event).days)
        date_score = max(0.0, 1 - days / Config.MATCH_DATE_WINDOW_DAYS)
    else:
        date_score = 0.0
    total = 0.40 * text + 0.25 * cat + 0.20 * loc + 0.15 * date_score
    if text == 0:            # no shared keywords at all -> category/place/date alone isn't evidence
        total *= 0.6
    return round(total, 3)


def find_matches(item: Item, create_records=True, notify_users=True):
    """Match `item` against open items of the opposite kind. Returns [(other, score)] sorted desc."""
    other_kind = "found" if item.kind == "lost" else "lost"
    candidates = Item.query.filter(
        Item.kind == other_kind, Item.status == "open", Item.user_id != item.user_id
    ).all()
    results = []
    for other in candidates:
        lost, found = (item, other) if item.kind == "lost" else (other, item)
        s = score_pair(lost, found)
        if s >= Config.MATCH_THRESHOLD:
            results.append((other, s))
            if create_records:
                rec = MatchRecord.query.filter_by(lost_id=lost.id, found_id=found.id).first()
                if not rec:
                    db.session.add(MatchRecord(lost_id=lost.id, found_id=found.id, score=s))
                    if notify_users:
                        pct = int(s * 100)
                        notify(lost.user_id, "Possible match found",
                               f"A found item “{found.title}” looks {pct}% similar to your lost report.",
                               f"/items/{found.id}", "match")
                        notify(found.user_id, "Possible owner found",
                               f"Your found item “{found.title}” matches a lost report ({pct}%).",
                               f"/items/{lost.id}", "match")
    if create_records:
        db.session.commit()
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def match_label(score):
    if score >= 0.70:
        return "Strong match"
    if score >= 0.55:
        return "Good match"
    return "Possible match"
