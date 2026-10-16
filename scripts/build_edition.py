import email.utils
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
articles = json.loads((ROOT / "data/articles.json").read_text())
sources = json.loads((ROOT / "data/sources.json").read_text())
source_map = {s["name"]: s for s in sources}

NOW = datetime.now(timezone.utc)
RIO = ZoneInfo("America/Sao_Paulo")
EDITION_DATE = NOW.astimezone(RIO).date().isoformat()

WINDOW_DAYS = 7
WINDOW_START = NOW - timedelta(days=WINDOW_DAYS)
FUTURE_GRACE_HOURS = 6

BLOCKED_SOURCES = {
    "Brand New", "BP&O", "Design Week", "Communication Arts",
    "Creative Review", "DIELINE",
}

GRAPHIC_SOURCES = {
    "It's Nice That", "Creative Boom", "Abduzeedo",
    "Packaging of the World", "SiteInspire", "Typewolf", "Slanted",
    "Design, Explained", "Into Design Systems + AI", "Bits to Brands",
    "Why Design Is Hard", "The Real Brand Life", "Logo Histories",
    "Typeverything Fonts",
}

GRAPHIC_FOCUS = {
    "DESIGN", "BRAND", "WEB", "TYPE", "PRINT", "PACKAGING", "EDITORIAL",
}

GRAPHIC_POSITIVE = {
    "design", "graphic design", "brand design", "branding", "identity",
    "logo", "wordmark", "typography", "typeface", "font", "lettering",
    "poster", "print", "editorial", "magazine", "book design",
    "book cover", "album cover", "campaign", "art direction",
    "art director", "creative direction", "web design", "website",
    "web typography", "interface", "ui", "visual identity", "rebrand",
    "wayfinding", "signage", "publication", "zine", "brochure", "catalog",
    "lookbook", "packaging",
}

GRAPHIC_NEGATIVE = {
    "architecture", "architectural", "interior", "interiors", "furniture",
    "chair", "table", "lighting", "building", "house", "apartment",
    "real estate", "industrial design", "product design", "kitchen",
    "bathroom", "landscape architecture", "urban planning",
    "restaurant interior", "hotel interior", "fashion collection",
}

def parsed_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            dt = email.utils.parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

def item_age_days(item):
    dt = parsed_date(item.get("publishedAt") or item.get("pubDate") or "")
    if not dt:
        return None
    return max(0.0, (NOW - dt).total_seconds() / 86400.0)

def in_seven_day_window(item):
    dt = parsed_date(item.get("publishedAt") or item.get("pubDate") or "")
    if dt:
        return WINDOW_START <= dt <= NOW + timedelta(hours=FUTURE_GRACE_HOURS)
    # Product/release HTML pages sometimes omit dates. For software/AI,
    # the current observed page is still useful as a live signal.
    return item.get("sourceKind") in {"software", "ai"} and bool(item.get("link"))

for item in articles:
    src = source_map.get(item.get("source", ""), {})
    dt = parsed_date(item.get("publishedAt") or item.get("pubDate") or "")
    age_days = item_age_days(item)
    fresh = in_seven_day_window(item)

    if dt:
        item["publishedAt"] = dt.isoformat()

    item["sourcePriority"] = float(src.get("priority", item.get("sourcePriority", 3)))
    item["sourceRole"] = src.get("role", item.get("sourceRole", "editorial"))
    item["designScope"] = src.get("designScope", item.get("designScope", ""))
    item["designFocus"] = src.get("designFocus", item.get("designFocus", []))
    item["sourceCountry"] = (
        "BR" if item.get("source") in {"MANDA REFS", "Tira do papel", "Bits to Brands"}
        else ""
    )
    item["fresh7"] = bool(fresh)
    item["ageDays"] = round(age_days, 2) if age_days is not None else None

    if age_days is None:
        recency = 5.2 if fresh else 0.0
    else:
        recency = max(0.0, 8.0 - (age_days / WINDOW_DAYS) * 8.0)

    image_bonus = 4.0 if item.get("image") else 0.0
    creative = float(item.get("creativeScore", 0))
    priority = float(item["sourcePriority"])
    freshness_bonus = recency if fresh else 0.0

    item["recencyScore"] = round(freshness_bonus, 2)
    item["editorialScore"] = round(
        priority * 2.2 + creative * 1.5 + image_bonus + freshness_bonus,
        2,
    )

def fresh_pool(pool):
    return [
        x for x in pool
        if x.get("fresh7")
        and x.get("source") not in BLOCKED_SOURCES
        and not x.get("hideFromAiImpact")
    ]

def sort_key(item):
    return (
        float(item.get("editorialScore", 0)),
        float(item.get("recencyScore", 0)),
        1 if item.get("image") else 0,
        item.get("publishedAt", ""),
    )

def diverse_select(pool, limit, source_cap=2, used_ids=None):
    used_ids = used_ids if used_ids is not None else set()
    candidates = [
        x for x in pool
        if x.get("id") not in used_ids
        and x.get("source") not in BLOCKED_SOURCES
    ]
    ranked = sorted(candidates, key=sort_key, reverse=True)

    selected = []
    counts = {}

    # First pass: one reference per source before allowing repeats.
    for item in ranked:
        src = item.get("source", "")
        if counts.get(src, 0):
            continue
        selected.append(item)
        used_ids.add(item.get("id"))
        counts[src] = 1
        if len(selected) >= limit:
            return selected

    # Second pass: fill the section while respecting the source cap.
    for item in ranked:
        if item.get("id") in used_ids:
            continue
        src = item.get("source", "")
        if counts.get(src, 0) >= source_cap:
            continue
        selected.append(item)
        used_ids.add(item.get("id"))
        counts[src] = counts.get(src, 0) + 1
        if len(selected) >= limit:
            break

    return selected

def is_graphic_design(item):
    if not item.get("fresh7") or not item.get("image"):
        return False
    if item.get("source") in BLOCKED_SOURCES:
        return False
    if item.get("sourceKind") in {"software", "ai"}:
        return False

    source = item.get("source", "")
    scope = item.get("designScope", "")
    focus = set(item.get("designFocus", []))
    blob = (
        str(item.get("title", ""))
        + " " + str(item.get("description", ""))
        + " " + " ".join(item.get("categories", []))
    ).lower()

    negative_hits = sum(1 for term in GRAPHIC_NEGATIVE if term in blob)
    positive_hits = sum(1 for term in GRAPHIC_POSITIVE if term in blob)
    focused = bool(focus.intersection(GRAPHIC_FOCUS))

    if source in {"SiteInspire", "Typewolf", "Slanted", "Logo Histories", "Typeverything Fonts"}:
        return negative_hits == 0 or positive_hits >= 2

    if source in GRAPHIC_SOURCES and (focused or positive_hits >= 2):
        if negative_hits >= 2 and positive_hits < 3:
            return False
        return True

    if scope in {
        "graphic", "graphic-packaging", "graphic-thinking", "web",
        "typography", "typography-web", "graphic-typography", "branding",
        "identity-history", "web-systems",
    }:
        return focused or positive_hits >= 2

    if negative_hits >= 2:
        return False
    return focused and positive_hits >= 2

fresh_articles = fresh_pool(articles)

culture = [
    x for x in fresh_articles
    if x.get("sourceKind") in {"culture", "visual-newsletter"}
]
visual = [x for x in fresh_articles if x.get("image")]
graphic = [x for x in fresh_articles if is_graphic_design(x)]
tool = [x for x in fresh_articles if x.get("sourceKind") == "software"]
ai = [
    x for x in fresh_articles
    if x.get("sourceKind") == "ai"
    and float(x.get("creativeScore", 0)) > 0
]
thinking = [
    x for x in fresh_articles
    if x.get("sourceKind") in {"thinking", "newsletter", "visual-newsletter"}
]

used = set()

hero_pool = [x for x in culture if x.get("image")] or visual
big_thing = diverse_select(hero_pool, 1, source_cap=1, used_ids=used)

signals = diverse_select(
    [x for x in fresh_articles if x.get("id") not in used],
    5,
    source_cap=1,
    used_ids=used,
)

graphic_design = diverse_select(
    [x for x in graphic if x.get("id") not in used],
    18,
    source_cap=2,
    used_ids=used,
)

tool_watch = diverse_select(
    [x for x in tool if x.get("id") not in used],
    6,
    source_cap=1,
    used_ids=used,
)

ai_impact = diverse_select(
    [x for x in ai if x.get("id") not in used],
    6,
    source_cap=1,
    used_ids=used,
)

wild = diverse_select(
    [x for x in thinking if x.get("id") not in used],
    5,
    source_cap=1,
    used_ids=used,
)

# FEAST is broad visual abundance, but it uses the exact same 7-day window.
feast = diverse_select(
    [x for x in visual if x.get("id") not in used],
    20,
    source_cap=2,
    used_ids=used,
)

def translation(item):
    blob = (
        str(item.get("title", ""))
        + " " + str(item.get("description", ""))
        + " " + " ".join(item.get("categories", []))
    ).lower()

    if any(k in blob for k in ["type", "typography", "font", "lettering"]):
        return "Borrow the typographic move. Change the message."
    if any(k in blob for k in ["brand", "identity", "logo", "campaign"]):
        return "Study the identity logic. Rebuild it for an unrelated subject."
    if any(k in blob for k in ["motion", "animation", "video"]):
        return "Freeze one motion principle and turn it into a static composition."
    if any(k in blob for k in ["ai", "model", "agent", "workflow"]):
        return "Take the new capability. Remove the default behavior."
    if any(k in blob for k in ["object", "product", "architecture", "space"]):
        return "Extract the geometry/material relationship and recompose it in 2D."
    return "Steal the principle, not the surface. Change the context."

make_from = feast[0] if feast else (signals[0] if signals else None)
make_something = {
    "reference": make_from.get("title", "") if make_from else "",
    "source": make_from.get("source", "") if make_from else "",
    "instruction": (
        translation(make_from)
        if make_from
        else "Pick one reference. Extract the principle. Change one variable."
    ),
}

source_health = []
for src in sources:
    name = src.get("name", "")
    total_items = sum(1 for x in articles if x.get("source") == name)
    fresh_items = sum(1 for x in fresh_articles if x.get("source") == name)

    if name in BLOCKED_SOURCES:
        status = "BLOCKED"
    elif fresh_items:
        status = "LIVE"
    else:
        status = "QUIET"

    source_health.append({
        "name": name,
        "kind": src.get("kind", "culture"),
        "items": fresh_items,
        "totalItems": total_items,
        "status": status,
    })

edition = {
    "editionDate": EDITION_DATE,
    "generatedAt": NOW.isoformat(),
    "windowDays": WINDOW_DAYS,
    "windowStart": WINDOW_START.isoformat(),
    "counts": {
        "all": len(articles),
        "fresh7": len(fresh_articles),
        "visual": len(visual),
        "graphicDesign": len(graphic_design),
        "culture": len(culture),
        "toolWatch": len(tool_watch),
        "aiImpact": len(ai_impact),
    },
    "bigThing": big_thing,
    "signals": signals,
    "visualFeast": feast,
    "graphicDesign": graphic_design,
    "toolWatch": tool_watch,
    "aiImpact": ai_impact,
    "wild": wild,
    "makeSomething": make_something,
    "sourceHealth": source_health,
}

(ROOT / "data/daily.json").write_text(
    json.dumps(edition, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

history_dir = ROOT / "data/history"
history_dir.mkdir(parents=True, exist_ok=True)
(history_dir / f"{EDITION_DATE}.json").write_text(
    json.dumps(edition, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(
    "Built edition", EDITION_DATE,
    f"using a rolling {WINDOW_DAYS}-day window",
    "with", len(big_thing), "hero,",
    len(signals), "signals,",
    len(feast), "feast,",
    len(tool_watch), "tool,",
    len(ai_impact), "AI and", len(wild), "wild references."
)
