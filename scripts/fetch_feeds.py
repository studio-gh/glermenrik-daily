import json
import re
import html
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sources = json.loads((ROOT / "data/sources.json").read_text())

UA = "Mozilla/5.0 (compatible; GlermenrikCreativeDen/1.3)"

BLOCKED_SOURCES = {"Brand New", "BP&O", "Design Week", "Communication Arts", "Creative Review"}
ACCESS_BLOCK_MARKERS = [
    "subscribe to read", "subscribe to continue reading", "become a member",
    "members only", "member-only", "only members can read", "paywall",
    "paid subscribers", "subscriber-only", "sign in to continue",
    "subscribe to unlock", "unlock this article"
]

def clean(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def fetch(url, timeout=15):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_feed(url, timeout=20):
    try:
        return fetch(url, timeout)
    except Exception as direct_exc:
        fallback = "https://api.rss2json.com/v1/api.json?rss_url=" + url
        try:
            raw = fetch(fallback, timeout)
            payload = json.loads(raw.decode("utf-8", "ignore"))
            if payload.get("status") != "ok":
                raise RuntimeError(payload.get("message") or "rss2json returned non-ok status")
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except Exception:
            raise direct_exc

def fetch_og_image(url):
    try:
        raw = fetch(url).decode("utf-8", "ignore")
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']'
        ]
        for pattern in patterns:
            m = re.search(pattern, raw, re.I)
            if m:
                return urljoin(url, m.group(1).strip())
    except Exception:
        pass
    return ""

def classify(title, desc):
    text = (title + " " + desc).lower()
    rules = [
        ("AI", ["generative ai", "artificial intelligence", "ai assistant", "ai agent", "image model", "video model", "text-to-image", "multimodal", "firefly", "midjourney", "veo", "gemini", "gpt-", "claude", "runway"]),
        ("MOTION", ["motion", "animation", "video", "after effects", "premiere", "lottie"]),
        ("IMAGE", ["image", "photo", "photoshop", "illustrator", "visual", "render"]),
        ("DESIGN", ["design", "figma", "canva", "typography", "brand", "creative cloud", "indesign"]),
        ("3D", ["3d", "blender", "geometry nodes", "substance"])
    ]
    return [name for name, words in rules if any(word in text for word in words)] or ["TECH"]

def parse_rss2json(raw):
    payload = json.loads(raw.decode("utf-8", "ignore"))
    if payload.get("status") != "ok":
        return []
    items = []
    for e in payload.get("items", []):
        enclosure = e.get("enclosure") or {}
        items.append({
            "title": clean(e.get("title", "")),
            "description": clean(e.get("content") or e.get("description") or ""),
            "link": e.get("link", "") or "",
            "pubDate": e.get("pubDate", "") or e.get("published_at", "") or "",
            "image": e.get("thumbnail", "") or enclosure.get("link", ""),
            "categories": [str(c).upper() for c in (e.get("categories") or [])],
        })
    return items

def is_access_blocked(item):
    blob = (item.get("title", "") + " " + item.get("description", "")).lower()
    return any(marker in blob for marker in ACCESS_BLOCK_MARKERS)

def parse_feed(raw):
    if raw.lstrip().startswith(b"{"):
        try:
            return parse_rss2json(raw)
        except Exception:
            return []
    root = ET.fromstring(raw)
    items = []
    entries = list(root.findall(".//item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))
    for e in entries:
        title = clean(e.findtext("title") or e.findtext("{http://www.w3.org/2005/Atom}title"))
        link = e.findtext("link") or ""
        atom_link = e.find("{http://www.w3.org/2005/Atom}link")
        if atom_link is not None:
            link = link or atom_link.attrib.get("href", "")
        desc = clean(
            e.findtext("description")
            or e.findtext("{http://www.w3.org/2005/Atom}summary")
            or e.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
        )
        pub = (
            e.findtext("pubDate")
            or e.findtext("{http://www.w3.org/2005/Atom}published")
            or e.findtext("{http://www.w3.org/2005/Atom}updated")
            or ""
        )
        cats = [clean(c.text).upper() for c in e.findall("category") if c.text]
        image = ""
        for node in [
            e.find("{http://search.yahoo.com/mrss/}content"),
            e.find("{http://search.yahoo.com/mrss/}thumbnail"),
            e.find("enclosure")
        ]:
            if node is not None:
                image = node.attrib.get("url") or node.attrib.get("href") or ""
                if image:
                    break
        if not image:
            raw_html = e.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or e.findtext("description") or ""
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', raw_html, re.I)
            if m:
                image = m.group(1)
        if title and link:
            items.append({
                "title": title,
                "description": desc[:500],
                "link": link,
                "pubDate": pub,
                "image": image,
                "categories": cats
            })
    return items

def parse_html_source(raw, src):
    text_content = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw.decode("utf-8", "ignore"), flags=re.I | re.S)
    found = []
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>\s*){0,3}([^<>]{12,180})'
    for m in re.finditer(pattern, text_content, re.I):
        link, title = m.group(1), clean(m.group(2))
        link = urljoin(src["url"], link)
        low = link.lower()
        if any(bad in low for bad in ["facebook", "instagram", "linkedin", "youtube", "twitter", "mailto:", "/search", "/login", "/contact", "/careers", "/enterprise", "/docs/"]):
            continue
        if src.get("product") == "Blender" and "blender.org/releases/" not in low:
            continue
        if src.get("product") == "Midjourney" and "updates.midjourney.com/" not in low:
            continue
        if src.get("product") == "Midjourney" and low.rstrip("/") == "https://updates.midjourney.com":
            continue
        if src.get("product") in ("Adobe", "Firefly") and "/publish/" not in low:
            continue
        if src.get("product") == "Canva" and "/newsroom/news/" not in low:
            continue
        if src.get("product") == "Runway" and not any(part in low for part in ["/news/", "/research/", "/introducing/", "/product/"]):
            continue
        if src.get("product") == "Logo Histories" and "/p/" not in low:
            continue
        if len(title) < 12 or title.lower() in {"read more", "learn more", "discover more", "home", "news", "terms of use", "privacy policy", "subscribe", "contact"}:
            continue
        found.append((title, link))

    seen = set()
    out = []
    for title, link in found:
        key = (title, link)
        if key not in seen:
            seen.add(key)
            out.append((title, link))
    return out[:18]

rows = []

for src in sources:
    if src.get("name") in BLOCKED_SOURCES:
        print("[SKIP]", src["name"], "blocked by access policy")
        continue
    try:
        items = []
        if src.get("feed"):
            items = parse_feed(fetch_feed(src["feed"]))
            items = [x for x in items if not is_access_blocked(x)]
        else:
            for title, link in parse_html_source(fetch(src["url"]), src):
                items.append({
                    "title": title,
                    "description": "",
                    "link": link,
                    "pubDate": "",
                    "image": "",
                    "categories": []
                })

        if src.get("kind") in ("software", "ai"):
            for item in items[:10]:
                if not item.get("image") and item.get("link"):
                    item["image"] = fetch_og_image(item["link"])

        for item in items[:12]:
            cats = list(dict.fromkeys(
                (src.get("territories") or [])
                + classify(item["title"], item.get("description", ""))
                + (item.get("categories") or [])
            ))
            item.update({
                "access": "free",
                "source": src["name"],
                "sourceUrl": src["url"],
                "sourceKind": src.get("kind", "culture"),
                "product": src.get("product", ""),
                "territory": (src.get("territories") or ["WILD"])[0],
                "categories": cats,
                "id": hashlib.sha256((src["name"] + "|" + item["link"]).encode()).hexdigest()[:16],
                "section": "TOOL WATCH" if src.get("kind") == "software" else ("AI IMPACT" if src.get("kind") == "ai" else "CULTURE"),
                "designScope": src.get("designScope", ""),
                "designFocus": src.get("designFocus", [])
            })
            rows.append(item)

    except Exception as exc:
        print("[WARN]", src["name"], exc)

blender_rows = [x for x in rows if x.get("product") == "Blender"]
other_rows = [x for x in rows if x.get("product") != "Blender"]

def blender_version(item):
    m = re.search(r"Blender\s+(\d+)\.(\d+)", item.get("title", ""), re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

blender_rows = sorted(blender_rows, key=blender_version, reverse=True)[:4]
rows = other_rows + blender_rows

seen = set()
final = []
for item in rows:
    key = item["link"].split("#")[0]
    if key in seen:
        continue
    seen.add(key)
    final.append(item)

creative_terms = [
    "design", "creative", "image", "video", "visual", "art", "photoshop",
    "illustrator", "figma", "canva", "blender", "firefly", "midjourney",
    "runway", "motion", "typography", "brand", "creator", "content",
    "camera", "music", "animation", "render", "workflow", "agent",
    "multimodal", "model", "editing"
]
noise_terms = [
    "enterprise sales", "careers", "jobs", "funding round",
    "quarterly results", "financial results", "board appointment",
    "recruiting", "sales team", "office opening", "documentation",
    "customer stories", "for education"
]

for item in final:
    blob = (item["title"] + " " + item.get("description", "")).lower()
    score = sum(1 for term in creative_terms if term in blob)
    if item["sourceKind"] == "ai":
        if any(term in blob for term in noise_terms) and score < 2:
            score = 0
        if item.get("product") in ("OpenAI", "Google AI") and not any(term in blob for term in ["image", "video", "visual", "creative", "design", "multimodal", "vision", "voice", "canvas", "generation"]):
            score = 0
        if item.get("product") in ("Midjourney", "Runway", "Firefly"):
            score += 2
        if item.get("product") in ("OpenAI", "Google AI") and any(term in blob for term in ["image", "video", "creative", "design", "multimodal", "gpt-", "gemini", "veo"]):
            score += 2
    item["creativeScore"] = score
    if item["sourceKind"] == "ai" and score == 0:
        item["hideFromAiImpact"] = True

for item in final:
    if item["sourceKind"] == "software" and not item.get("image"):
        item["imageState"] = "placeholder"
    elif item["sourceKind"] == "ai" and not item.get("image"):
        item["imageState"] = "placeholder"

final.sort(
    key=lambda x: (
        x.get("sourceKind") == "ai",
        x.get("hideFromAiImpact", False) is False,
        x.get("creativeScore", 0),
        x.get("pubDate") or ""
    ),
    reverse=True
)

(ROOT / "data/articles.json").write_text(
    json.dumps(final[:350], ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print("Published", len(final[:350]), "references from", len(sources), "sources.")
