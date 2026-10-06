import json
import re
import email.utils
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
articles = json.loads((ROOT / "data/articles.json").read_text())
sources = json.loads((ROOT / "data/sources.json").read_text())
source_map = {s["name"]: s for s in sources}

NOW = datetime.now(timezone.utc)
RIO = ZoneInfo("America/Sao_Paulo")
edition_date = NOW.astimezone(RIO).date().isoformat()

def parsed_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
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

for item in articles:
    src = source_map.get(item.get("source", ""), {})
    dt = parsed_date(item.get("publishedAt") or item.get("pubDate", ""))
    age = max(0.0, (NOW - dt).total_seconds() / 3600.0) if dt else 168.0
    recency = max(0.0, 8.0 - age / 24.0)
    image_bonus = 4.0 if item.get("image") else 0.0
    priority = float(src.get("priority", item.get("sourcePriority", 3)))
    creative = float(item.get("creativeScore", 0))
    source_kind = item.get("sourceKind", src.get("kind", "culture"))
    item["sourcePriority"] = priority
    item["sourceRole"] = src.get("role", item.get("sourceRole", "editorial"))
    item["publishedAt"] = dt.isoformat() if dt else item.get("publishedAt", "")
    item["recencyScore"] = round(recency, 2)
    item["editorialScore"] = round(priority * 2.2 + creative * 1.4 + image_bonus + recency, 2)
    item["sourceCountry"] = "BR" if item.get("source") in {"MANDA REFS", "Tira do papel", "Bits to Brands"} else ""

def visible_pool(pool):
    return [x for x in pool if not x.get("hideFromAiImpact")]

def diverse_select(pool, limit, source_cap=2):
    selected = []
    counts = {}
    for item in sorted(pool, key=lambda x: (x.get("editorialScore", 0), x.get("publishedAt", "")), reverse=True):
        src = item.get("source", "")
        if counts.get(src, 0) >= source_cap:
            continue
        selected.append(item)
        counts[src] = counts.get(src, 0) + 1
        if len(selected) >= limit:
            break
    return selected

culture = [x for x in articles if x.get("sourceKind") in ("culture", "visual-newsletter", "archive")]
visual = [x for x in articles if x.get("image") and not x.get("hideFromAiImpact")]
tool = [x for x in articles if x.get("sourceKind") == "software"]
ai = visible_pool([x for x in articles if x.get("sourceKind") == "ai" and x.get("creativeScore", 0) > 0])
thinking = [x for x in articles if x.get("sourceKind") in ("thinking", "newsletter", "archive", "visual-newsletter")]

hero_pool = [x for x in culture if x.get("image")] or visual
big_thing = sorted(hero_pool, key=lambda x: (x.get("editorialScore", 0), x.get("publishedAt", "")), reverse=True)[:1]

signals_pool = [x for x in articles if x not in big_thing and not x.get("hideFromAiImpact")]
signals = diverse_select(signals_pool, 5, source_cap=1)

feast = diverse_select([x for x in visual if x not in big_thing], 20, source_cap=2)
tool_watch = diverse_select(tool, 6, source_cap=1)
ai_impact = diverse_select(ai, 6, source_cap=1)
wild = diverse_select(thinking, 5, source_cap=1)

# Lightweight editorial translation. This is intentionally deterministic and transparent.
def translation(item):
    blob = (item.get("title", "") + " " + item.get("description", "") + " " + " ".join(item.get("categories", []))).lower()
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
    "instruction": translation(make_from) if make_from else "Pick one reference. Extract the principle. Change one variable.",
}

source_health = []
for src in sources:
    count = sum(1 for x in articles if x.get("source") == src.get("name"))
    source_health.append({
        "name": src.get("name"),
        "kind": src.get("kind", "culture"),
        "items": count,
        "status": "LIVE" if count else "QUIET"
    })

edition = {
    "editionDate": edition_date,
    "generatedAt": NOW.isoformat(),
    "counts": {
        "all": len(articles),
        "visual": len(visual),
        "culture": len(culture),
        "toolWatch": len(tool_watch),
        "aiImpact": len(ai_impact)
    },
    "bigThing": big_thing,
    "signals": signals,
    "visualFeast": feast,
    "toolWatch": tool_watch,
    "aiImpact": ai_impact,
    "wild": wild,
    "makeSomething": make_something,
    "sourceHealth": source_health
}

(ROOT / "data/daily.json").write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
history_dir = ROOT / "data/history"
history_dir.mkdir(parents=True, exist_ok=True)
(history_dir / f"{edition_date}.json").write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
print("Built edition", edition_date, "with", len(big_thing), "hero,", len(signals), "signals,", len(feast), "feast,", len(tool_watch), "tool,", len(ai_impact), "AI and", len(wild), "wild references.")