import json
import re
import html
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sources = json.loads((ROOT / "data/sources.json").read_text())

UA = "Mozilla/5.0 (compatible; GlermenrikCreativeDen/1.4)"
ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8"

# Sources the desk deliberately does not ingest because they are known to require
# membership/subscription for meaningful archive access.
BLOCKED_SOURCES = {
    "Brand New",
    "BP&O",
    "Design Week",
    "Communication Arts",
    "Creative Review",
    "DIELINE",
}

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

def fetch(url, timeout=20):
    req = Request(url, headers={"User-Agent": UA, "Accept": ACCEPT})
    with urlopen(req, timeout=timeout) as response:
        return response.read()

def fetch_rss2json(url, timeout=25):
    # Encode the RSS URL as a real query parameter. The old implementation
    # could break when a feed URL itself contained query parameters.
    fallback = "https://api.rss2json.com/v1/api.json?rss_url=" + quote(url, safe="")
    raw = fetch(fallback, timeout)
    payload = json.loads(raw.decode("utf-8", "ignore"))
    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("message") or "rss2json returned non-ok status")
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")

def fetch_feed(url, timeout=25):
    try:
        return fetch(url, timeout)
    except Exception as direct_exc:
        try:
            return fetch_rss2json(url, timeout)
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
            match = re.search(pattern, raw, re.I)
            if match:
                return urljoin(url, match.group(1).strip())
    except Exception:
        pass
    return ""

def classify(title, desc):
    text = (title + " " + desc).lower()
    rules = [
        ("AI", [
            "generative ai", "artificial intelligence", "ai assistant", "ai agent",
            "image model", "video model", "text-to-image", "multimodal",
            "firefly", "midjourney", "veo", "gemini", "gpt-", "claude", "runway"
        ]),
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
    for entry in payload.get("items", []):
        enclosure = entry.get("enclosure") or {}
        items.append({
            "title": clean(entry.get("title", "")),
            "description": clean(entry.get("content") or entry.get("description") or ""),
            "link": entry.get("link", "") or "",
            "pubDate": entry.get("pubDate", "") or entry.get("published_at", "") or "",
            "image": entry.get("thumbnail", "") or enclosure.get("link", ""),
            "categories": [str(c).upper() for c in (entry.get("categories") or [])],
        })
    return items

def is_access_blocked(item):
    blob = (item.get("title", "") + " " + item.get("description", "")).lower()
    return any(marker in blob for marker in ACCESS_BLOCK_MARKERS)

def parse_feed(raw):
    if raw.lstrip().startswith(b"{"):
        return parse_rss2json(raw)

    root = ET.fromstring(raw)
    items = []
    entries = list(root.findall(".//item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))

    for entry in entries:
        title = clean(
            entry.findtext("title")
            or entry.findtext("{http://www.w3.org/2005/Atom}title")
        )
        link = entry.findtext("link") or ""
        atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
        if atom_link is not None:
            link = link or atom_link.attrib.get("href", "")

        desc = clean(
            entry.findtext("description")
            or entry.findtext("{http://www.w3.org/2005/Atom}summary")
            or entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
        )
        pub = (
            entry.findtext("pubDate")
            or entry.findtext("{http://www.w3.org/2005/Atom}published")
            or entry.findtext("{http://www.w3.org/2005/Atom}updated")
            or ""
        )
        cats = [
            clean(c.text).upper()
            for c in entry.findall("category")
            if c.text
        ]

        image = ""
        for node in [
            entry.find("{http://search.yahoo.com/mrss/}content"),
            entry.find("{http://search.yahoo.com/mrss/}thumbnail"),
            entry.find("enclosure"),
        ]:
            if node is not None:
                image = node.attrib.get("url") or node.attrib.get("href") or ""
                if image:
                    break

        if not image:
            raw_html = (
                entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                or entry.findtext("description")
                or ""
            )
            match = re.search(r'<img[^>]+src=["\']([^"\']+)', raw_html, re.I)
            if match:
                image = match.group(1)

        if title and link:
            items.append({
                "title": title,
                "description": desc[:700],
                "link": link,
                "pubDate": pub,
                "image": image,
                "categories": cats,
            })

    return items

def parse_feed_with_recovery(url):
    raw = fetch_feed(url)
    try:
        return parse_feed(raw)
    except Exception as parse_exc:
        # Some feeds return malformed XML while still exposing valid data
        # through rss2json. Recover before declaring the source broken.
        try:
            return parse_rss2json(fetch_rss2json(url))
        except Exception:
            raise parse_exc

def parse_html_source(raw, src):
    text_content = re.sub(
        r"<(script|style|noscript)[^>]*>.*?</\1>",
        " ",
        raw.decode("utf-8", "ignore"),
        flags=re.I | re.S,
    )
    found = []
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>\s*){0,3}([^<>]{12,180})'

    for match in re.finditer(pattern, text_content, re.I):
        link, title = match.group(1), clean(match.group(2))
        link = urljoin(src["url"], link)
        low = link.lower()

        if any(bad in low for bad in [
            "facebook", "instagram", "linkedin", "youtube", "twitter", "mailto:",
            "/search", "/login", "/contact", "/careers", "/enterprise", "/docs/"
        ]):
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
        if src.get("product") == "Runway" and not any(
            part in low for part in ["/news/", "/research/", "/introducing/", "/product/"]
        ):
            continue
        if src.get("product") == "Logo Histories" and "/p/" not in low:
            continue

        if len(title) < 12 or title.lower() in {
            "read more", "learn more", "discover more", "home", "news",
            "terms of use", "privacy policy", "subscribe", "contact"
        }:
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
    name = src.get("name", "")
    if name in BLOCKED_SOURCES or src.get("accessPolicy") in {"blocked", "paid", "membership"}:
        print("[SKIP]", name, "blocked by access policy")
        continue

    try:
        items = []
        if src.get("feed"):
            items = parse_feed_with_recovery(src["feed"])
            items = [item for item in items if not is_access_blocked(item)]
        else:
            for title, link in parse_html_source(fetch(src["url"]), src):
                items.append({
                    "title": title,
                    "description": "",
                    "link": link,
                    "pubDate": "",
                    "image": "",
                    "categories": [],
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
                "access": src.get("accessPolicy", "unknown"),
                "source": name,
                "sourceUrl": src["url"],
                "sourceKind": src.get("kind", "culture"),
                "product": src.get("product", ""),
                "territory": (src.get("territories") or ["WILD"])[0],
                "categories": cats,
                "id": hashlib.sha256(
                    (name + "|" + item["link"]).encode()
                ).hexdigest()[:16],
                "section": (
                    "TOOL WATCH"
                    if src.get("kind") == "software"
                    else ("AI IMPACT" if src.get("kind") == "ai" else "CULTURE")
                ),
                "designScope": src.get("designScope", ""),
                "designFocus": src.get("designFocus", []),
            })
            rows.append(item)

    except Exception as exc:
        print("[WARN]", name, exc)

# Blender's release page can contain many version links. Keep the latest few.
blender_rows = [x for x in rows if x.get("product") == "Blender"]
other_rows = [x for x in rows if x.get("product") != "Blender"]

def blender_version(item):
    match = re.search(r"Blender\s+(\d+)\.(\d+)", item.get("title", ""), re.I)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)

blender_rows = sorted(blender_rows, key=blender_version, reverse=True)[:4]
rows = other_rows + blender_rows

seen = set()
final = []
for item in rows:
    key = item["link"].split("#")[0].rstrip("/")
    if key in seen:
        continue
    seen.add(key)
    final.append(item)

creative_terms = [
    "design", "creative", "image", "video", "visual", "art", "photoshop",
    "illustrator", "figma", "canva", "blender", "firefly", "midjourney",
    "runway", "motion", "typography", "brand", "creator", "content",
    "camera", "music", "animation", "render", "workflow", "agent",
    "multimodal", "model", "editing", "interface", "web", "packaging"
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
        if item.get("product") in ("OpenAI", "Google AI") and not any(
            term in blob for term in [
                "image", "video", "visual", "creative", "design",
                "multimodal", "vision", "voice", "canvas", "generation"
            ]
        ):
            score = 0
        if item.get("product") in ("Midjourney", "Runway", "Firefly"):
            score += 2
        if item.get("product") in ("OpenAI", "Google AI") and any(
            term in blob for term in [
                "image", "video", "creative", "design", "multimodal",
                "gpt-", "gemini", "veo"
            ]
        ):
            score += 2

    item["creativeScore"] = score

    if item["sourceKind"] == "ai" and score == 0:
        item["hideFromAiImpact"] = True

    if item["sourceKind"] in ("software", "ai") and not item.get("image"):
        item["imageState"] = "placeholder"

final.sort(
    key=lambda x: (
        not x.get("hideFromAiImpact", False),
        x.get("creativeScore", 0),
        x.get("pubDate") or "",
    ),
    reverse=True,
)

(ROOT / "data/articles.json").write_text(
    json.dumps(final[:350], ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("Published", len(final[:350]), "references from", len(sources), "sources.")
