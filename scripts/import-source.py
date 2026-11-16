#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["lxml==6.1.1"]
# ///
"""Import public Agriculture-Vision pages into the local Astro content snapshot.

Requires lxml (also declared for uv run). With no flags, discover official pages
and download local media. With --inventory, reuse an existing crawl evidence file.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from lxml import html

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.agriculture-vision.com"
HOSTS = {"www.agriculture-vision.com", "agriculture-vision.com"}
UA = "Mozilla/5.0 (compatible; Agriculture-Vision public website migration)"
IMG_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
             "image/gif": "gif", "image/avif": "avif"}
BG_URL = re.compile(r'url\(["\x27]?([^)"\x27]+)["\x27]?\)')
COLS = {name: i for i, name in enumerate(
    "R6PoUb ibL1re c5RTEf II5mzb wNfPc qWD73c OwsYgb OiUrBf Clt0zb EehZO zQtlcf uQSCkd".split(), 1)}
SAFE_STYLE = {
    "font-size": r"(?:[1-9][0-9]?)(?:\.\d+)?(?:px|pt|em|rem)",
    "font-weight": r"(?:[1-9]00|bold|normal)",
    "font-style": r"(?:normal|italic|oblique)",
    "font-variant": r"(?:normal|small-caps)",
    "text-align": r"(?:left|right|center|justify|start|end)",
    "text-decoration": r"(?:none|underline|line-through)",
    "color": r"(?:\#[a-fA-F0-9]{3,8}|rgba?\([\d.,%\s]+\))",
    "vertical-align": r"(?:baseline|middle|sub|super)",
}
ALLOWED_TAGS = set("a abbr b blockquote br caption code dd del details div dl dt em figcaption figure h1 h2 h3 h4 h5 h6 i img li mark ol p pre s small span strong sub summary sup table tbody td th thead tr u ul".split())

def origin_path(link: str, base: str = SITE) -> str | None:
    u = urlsplit(urljoin(base, link))
    path = u.path.rstrip("/") or "/"
    if u.scheme not in {"http", "https"} or u.netloc.lower() not in HOSTS or path.startswith(("/_/", "/view/", "/site/")):
        return None
    return path

def read_url(url: str, timeout: int = 18) -> tuple[bytes, str, str]:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as f:
        return f.read(), f.headers.get_content_type(), f.url

def load_pages(inventory: Path | None) -> list[tuple[str, str, html.HtmlElement]]:
    def tree(data: bytes) -> html.HtmlElement:
        return html.parse(BytesIO(data), parser=html.HTMLParser(encoding="utf-8")).getroot()
    if inventory:
        found = json.loads(inventory.read_text())
        failed = [e["path"] for e in found["entries"] if not (e.get("raw") and e.get("status") == 200)]
        if failed:
            raise ValueError("Inventory contains uncaptured pages: " + ", ".join(failed))
        return [(e["path"], e["url"], tree((inventory.parent / e["raw"]).read_bytes()))
                for e in found["entries"]]
    def fetch(path):
        content, content_type, url = read_url(SITE + path)
        if content_type not in ("text/html", "application/xhtml+xml") or origin_path(url) is None:
            raise ValueError(f"Unexpected response for {path}: {content_type}, {url}")
        return path, url, tree(content)
    found = {}
    pending = ["/"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        while pending:
            discovered = set()
            for path, url, page in pool.map(fetch, pending):
                if not page.xpath("//section[contains(concat(' ',normalize-space(@class),' '),' yaqOZd ')]"):
                    raise ValueError(f"No published page body for {path}")
                found[path] = (path, url, page)
                discovered.update(origin_path(link, url) for link in page.xpath("//a/@href"))
            pending = sorted(discovered - {None} - found.keys())
            if len(found) + len(pending) > 200:
                raise ValueError("Scope exceeded 200 pages; inspect source navigation before continuing")
    return [found[path] for path in sorted(found)]

def background(style: str) -> str:
    match = BG_URL.search(style or "")
    return match.group(1) if match else ""

def bits(node) -> set[str]:
    return set(node.get("class", "").split())

def clean_style(node) -> str:
    props = []
    for entry in node.get("style", "").split(";"):
        key, sep, value = (s.strip() for s in entry.partition(":"))
        if sep and key in SAFE_STYLE and re.fullmatch(SAFE_STYLE[key], value):
            props.append(f"{key}:{value}")
    return ";".join(props)

def attrs(values) -> str:
    return "".join(f' {name}="{escape(str(value), quote=True)}"' for name, value in values.items()
                   if value is not None)

def plain(n):
    return " ".join(n.text_content().split())

def span_of(node, fallback=12):
    return next((COLS[x.removeprefix("hJDwNd-AhqUyc-")]
                 for x in node.get("class", "").split()
                 if x.startswith("hJDwNd-AhqUyc-") and x.removeprefix("hJDwNd-AhqUyc-") in COLS), fallback)

def size_invariant(url: str) -> str:
    u = urlsplit(url)
    if (u.hostname or "").endswith(".googleusercontent.com"):
        return urlunsplit((u.scheme, u.netloc, re.sub(r"=(?:w\d+|h\d+)$", "", u.path), u.query, u.fragment))
    return url


def image_extension(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    if data.startswith(b"\xff\xd8\xff"): return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")): return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return "webp"
    if data[4:12] in (b"ftypavif", b"ftypavis"): return "avif"
    return None


@dataclass
class Importer:
    paths: set[str]
    urls: dict[str, str] = field(default_factory=dict)
    counts: Counter = field(default_factory=Counter)
    asset_issues: list[dict] = field(default_factory=list)
    unresolved: dict[str, set[str]] = field(default_factory=dict)
    media: dict[str, str] = field(default_factory=dict)
    source_occurrences: dict[str, set[tuple[str, str, str]]] = field(default_factory=dict)
    missing_alts: int = 0

    def asset(self, url: str, source: str, is_background=False) -> str:
        u = urljoin(source, url)
        owner = urlsplit(u)
        actual_url = u
        if owner.scheme == "https" and (owner.hostname == "googleusercontent.com"
                or (owner.hostname or "").endswith(".googleusercontent.com")
                or owner.hostname == "ssl.gstatic.com"):
            # Google may append a requested/square/circle crop to the same resource; treat those
            # as separate assets. For enormous carousel requests, use a web-scale maximum.
            if owner.hostname.endswith(".googleusercontent.com") and re.search(r"=w16383$", u):
                u = re.sub(r"=w16383$", "=w1600" if is_background else "=w1280", u)
            key = sha256(u.encode()).hexdigest()[:20]
            self.urls[key] = u
            self.source_occurrences.setdefault(key, set()).add((source, actual_url, "background" if is_background else "image"))
            return f"@MEDIA:{key}@"
        raise ValueError(f"Unexpected non-localizable image URL on {source}: {u}")

    def link(self, address, source):
        if not address: return None
        if address.startswith("#"):
            return address
        url = urljoin(source, address)
        parts = urlsplit(url)
        if parts.hostname in ("www.google.com", "google.com") and parts.path == "/url":
            params = parse_qs(parts.query)
            url = (params.get("q") or params.get("url") or [""])[0]
            parts = urlsplit(url)
        if parts.scheme not in ("https", "http", "mailto", "tel"):
            return None
        p = origin_path(url)
        if p:
            if p in self.paths:
                return urlunsplit(("", "", p, parts.query, parts.fragment))
            self.unresolved.setdefault(source, set()).add(url)
        return url

    def node(self, n, source, *, workshop=False, hero=False, portrait_alt=None):
        if not isinstance(n.tag, str):
            return ""
        tag = n.tag.lower()
        c = bits(n)
        if tag in {"script", "style", "svg", "noscript", "button", "input", "form", "object", "template"}:
            return ""
        if n.get("role") == "button" or n.get("aria-hidden") == "true" or "QV9O1" in c:
            return ""
        if n.get("data-autostart") is not None:
            frames = n.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," nQBJnb ")]')
            caps = n.xpath('.//*[@jsname="vM03ic"]')
            slides = []
            for i, frame in enumerate(frames):
                url = background(frame.get("style", ""))
                if not url: continue
                caption = plain(caps[i]) if i < len(caps) else ""
                alt = caption or frame.get("aria-label") or f"Dataset example {i + 1}"
                cap = f"<figcaption>{escape(caption)}</figcaption>" if caption else ""
                slides.append(f'<figure><img{attrs({"src": self.asset(url, source), "alt": alt, "loading": "lazy", "decoding": "async"})}>{cap}</figure>')
            if not slides:
                raise ValueError(f"No source carousel frames on {source}")
            self.counts["galleries"] += 1
            self.counts["gallery_images"] += len(slides)
            return f'<div class="source-gallery" role="region" aria-label="Image examples" tabindex="0">{"".join(slides)}</div>'
        if "iwQgFb" in c or tag == "hr":
            return '<hr class="source-rule">'
        if tag in {"iframe", "embed"}:
            url = self.link(n.get("src"), source)
            if not url: raise ValueError(f"Unresolvable embedded content on {source}")
            label = n.get("title") or "View embedded content"
            self.counts["external_embeds"] += 1
            return f'<p class="source-embed"><a{attrs({"href":url})}>{escape(label)}</a></p>'
        if tag == "img":
            url = n.get("src") or n.get("data-src")
            if not url: return ""
            alt = n.get("alt") or n.get("aria-label") or portrait_alt or ""
            if not alt: self.missing_alts += 1
            self.counts["inline_images"] += 1
            image_props = {"src": self.asset(url, source), "alt": alt,
                           "loading": "lazy", "decoding": "async"}
            if n.get("width", "").isdigit(): image_props["width"] = n.get("width")
            if n.get("height", "").isdigit(): image_props["height"] = n.get("height")
            sizing = []
            # Google Sites crop wrappers store an aspect ratio and the crop focal offsets.
            anc = n.getparent()
            for _ in range(4):
                if anc is None: break
                style = anc.get("style", "")
                m = re.search(r'padding-top:\s*([\d.]+)%', style)
                if m and float(m.group(1)) > 0:
                    sizing.append(f"aspect-ratio:100/{m.group(1)}")
                    break
                anc = anc.getparent()
            if sizing:
                image_props["style"] = ";".join(sizing)
                image_props["class"] = "source-cropped-image"
            return f'<img{attrs(image_props)}>'
        if tag == "br":
            return "<br>"
        kids = escape(n.text or "") + "".join(
            self.node(x, source, workshop=workshop, hero=hero, portrait_alt=portrait_alt)
            + escape(x.tail or "") for x in n)
        cls = None
        if workshop and hero and tag == "h2":
            tag = "h1"
        elif workshop and hero and tag == "h3":
            # Heading order is improved without changing words, styling or public fragment IDs.
            cls = "source-hero-context" if plain(n).lower().startswith("in conjunction") else "source-hero-kicker"
            tag = "p"
        if tag == "a":
            dest = self.link(n.get("href"), source)
            if not dest: return kids
            if not kids.strip() and n.get("aria-label"):
                kids = escape(n.get("aria-label"))
            link_cls = "source-button" if "FKF6mc" in c else None
            a = {"href": dest, "class": link_cls,
                 "aria-label": n.get("aria-label") if link_cls else None,
                 "id": n.get("id"), "style": clean_style(n) or None}
            return f"<a{attrs(a)}>{kids}</a>" if kids.strip() else ""
        if tag not in ALLOWED_TAGS:
            return kids
        style = clean_style(n)
        ident = n.get("id")
        if tag == "div":
            if "z6B8ye" in c or "t3iYD" in c or "CENy8b" in c:
                cls = "source-image"
            # Google container nesting is not needed by Astro.
            if not (cls or (ident and n.get("role") not in {"presentation"}) or style):
                return kids
        if tag == "span" and not (ident or style or cls):
            return kids
        if not kids.strip() and not ident: return ""
        props = {"id": ident, "class": cls, "style": style or None}
        for prop in ("colspan", "rowspan", "scope", "start", "value", "open"):
            value = n.get(prop)
            if value is not None and re.fullmatch(r"(?:[0-9]+|row|col|rowgroup|colgroup|)", value):
                props[prop] = value
        return f"<{tag}{attrs(props)}>{kids}</{tag}>"

    def page(self, route, source, doc):
        rendered = []
        workshop = route == "/" or re.fullmatch(r"/agriculture-vision-20\d\d", route) is not None
        for i, sec in enumerate(doc.xpath('//section[contains(concat(" ",normalize-space(@class)," ")," yaqOZd ")]')):
            cc = bits(sec)
            hero = i == 0 and "LB7kq" in cc
            props = {"id": sec.get("id"), "class": "source-section"}
            if hero:
                props["class"] += " source-hero " + ("source-workshop" if workshop else "source-page-title")
            if "WxWicb" in cc: props["class"] += " source-divider-section"
            if "lQAHbd" in cc: props["class"] += " source-section-tinted"
            bg_url = next((background(h.get("style", "")) for h in sec.xpath(
                './div[1]//*[contains(concat(" ",normalize-space(@class)," ")," IFuOkc ")]') if background(h.get("style", ""))), "")
            if hero and not bg_url and "O13XJf" in cc:
                bg_url = "https://ssl.gstatic.com/atari/images/impression-header.png"
            if bg_url:
                props["style"] = f"--hero-image:url({self.asset(bg_url, source,is_background=True)})"
            cols = []
            found = sec.xpath('./div/div[contains(concat(" ",normalize-space(@class)," ")," LS81yb ")]/div')
            for col in found:
                spacer = not plain(col) and not col.xpath('.//img|.//iframe|.//*[@data-autostart]|.//*[contains(@class, "iwQgFb")]')
                person = None
                if workshop and not hero and len(col.xpath('.//img')) == 1:
                    candidates = [plain(t) for t in col.xpath(".//h2|.//h3|.//p") if plain(t)]
                    if candidates and len(candidates[0].split()) in range(2, 6):
                        person = candidates[0]
                body = "" if spacer else self.node(col, source, workshop=workshop, hero=hero, portrait_alt=person)
                size = span_of(col)
                flags = "source-column"
                if spacer: flags += " source-spacer"
                if not spacer and "text-align: center" in " ".join(col.xpath(".//@style")):
                    flags += " source-column-centered"
                cols.append(f'<div class="{flags}" style="--span:{size}">{body}</div>')
            if not found:
                raise ValueError(f"Unexpected page section structure on {source}")
            if all(" source-spacer" in x for x in cols):
                continue
            rendered.append(f'<section{attrs(props)}><div class="source-row">{"".join(cols)}</div></section>')
        if not rendered:
            raise ValueError(f"Zero page sections imported from {source}")
        title = plain(doc.xpath("//title")[0]) if doc.xpath("//title") else "Agriculture-Vision"
        if workshop and route != "/" and title == "Vision for Agriculture":
            title += " - Agriculture-Vision " + route.rsplit("-", 1)[-1]
        return {"path": route, "title": title, "html": "\n".join(rendered), "source": source}

    def save_assets(self, report=None, local_map=None, offline=False):
        target = ROOT / "public" / "media"
        target.mkdir(parents=True, exist_ok=True)
        prior_failures = {e["source"]: e for e in json.loads(report.read_text())} if report else {}
        local_files = json.loads(local_map.read_text()) if local_map else {}
        if not isinstance(local_files, dict):
            raise ValueError("Local media map must be a JSON object of source URL to downloaded local path")
        by_size_invariant = {}
        # Only compare size variants with no crop/rotation/other modifiers. Maintain the
        # exact source mapping when both versions are available.
        for url, filename in local_files.items():
            if not isinstance(filename, str):
                raise ValueError(f"Expected a downloaded file path for {url}")
            by_size_invariant.setdefault(size_invariant(url), []).append(filename)
        def import_local(key, filename):
            disk_path = Path(filename)
            if not disk_path.is_absolute():
                disk_path = local_map.parent / disk_path
            data = disk_path.read_bytes()
            ext = image_extension(data)
            if not ext:
                raise ValueError(f"Downloaded browser file is not a recognized image: {disk_path.name}")
            path = target / f"{key}.{ext}"
            path.write_bytes(data)
            return path.name
        def download(x):
            key, url = x
            cached = sorted(target.glob(f"{key}.*"))
            if len(cached) == 1 and cached[0].stat().st_size > 32 and cached[0].suffix[1:] in IMG_TYPES.values():
                return key, cached[0].name, None
            if local_map:
                opt = by_size_invariant.get(size_invariant(url), [])
                filename = local_files.get(url) or (opt[0] if len(set(opt)) == 1 else None)
                if filename:
                    return key, import_local(key, filename), None
            if url in prior_failures:
                return key, None, prior_failures[url]
            if offline:
                return key, None, {"source": url, "error": "No local browser download provided"}
            for attempt in range(2):
                try:
                    data, mimetype, source = read_url(url)
                    if (mimetype not in IMG_TYPES or len(data) <= 32 or urlsplit(source).scheme != "https"
                            or image_extension(data) != IMG_TYPES[mimetype]):
                        raise ValueError(f"Unexpected media response {mimetype}, {len(data)} bytes")
                    path = target / f"{key}.{IMG_TYPES[mimetype]}"
                    path.write_bytes(data)
                    return key, path.name, None
                except Exception as e:
                    if attempt == 1:
                        return key, None, {"source": url, "error": str(e)}
                    time.sleep(0.3)
        with ThreadPoolExecutor(max_workers=25) as pool:
            for key, name, error in pool.map(download, self.urls.items()):
                if name:
                    self.media[key] = "/media/" + name
                else:
                    self.asset_issues.append(error)
        for old in target.iterdir():
            if old.is_file() and re.fullmatch(r"[0-9a-f]{20}\.[a-z]+", old.name) and old.stem not in self.urls:
                old.unlink()

    def resolve(self, string):
        # Keep rendering entirely local even when a source asset was blocked. Do not hide
        # that fact behind a broken image or replace it with an unrelated photograph.
        string = re.sub(r'<img src="@MEDIA:([0-9a-f]{20})@"([^>]*)>', self.resolve_image, string)
        string = re.sub(r' style="--hero-image:url\(@MEDIA:([0-9a-f]{20})@\)"',
                        lambda m: f' style="--hero-image:url({self.media[m[1]]})"' if m[1] in self.media else '', string)
        return string

    def resolve_image(self, match):
        key, rest = match.groups()
        if key in self.media:
            return f'<img src="{self.media[key]}"{rest}>'
        alt = re.search(r' alt="([^"]*)"', rest)
        label = alt[1] if alt and alt[1] else "Source image"
        return (f'<span class="source-image-unavailable" role="img" '
                f'aria-label="{label} (unavailable in local preview)" data-source-image="{key}">'
                'Image unavailable in preview</span>')

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--inventory", type=Path)
    cli.add_argument("--known-blocked-media", type=Path, help="Reuse a JSON list of already recorded media blocks instead of retrying them")
    cli.add_argument("--local-media-map", type=Path, help="JSON mapping of source image URLs to already acquired browser download paths")
    cli.add_argument("--offline-media", action="store_true", help="No media network downloads; use browser map and local cache")
    cli.add_argument("--strict-media", action="store_true", help="Return non-zero when any original asset is missing, after saving the audit")
    args = cli.parse_args()
    pages = load_pages(args.inventory)
    importer = Importer({p[0] for p in pages})
    converted = [importer.page(*p) for p in pages]
    logo = pages[0][2].xpath('//header//img/@src')
    logo_asset = importer.asset(logo[0], SITE) if logo else None
    print(f"Converted {len(converted)} pages. Localizing {len(importer.urls)} images.", flush=True)
    importer.save_assets(args.known_blocked_media, args.local_media_map, args.offline_media)
    for page in converted:
        page["html"] = importer.resolve(page["html"])
    dest = ROOT / "src" / "content"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "snapshot.json").write_text(json.dumps(converted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {"source": SITE, "route_count": len(converted), "images_local": len(importer.media),
                "images_expected": len(importer.urls), "images_missing": len(importer.asset_issues),
                "logo": importer.media.get(logo_asset.split(":")[1][:-1]) if logo_asset else None,
                "media_counts": dict(importer.counts), "images_without_alt_in_snapshot": importer.missing_alts,
                "unresolved_internal_links": {s: sorted(v) for s, v in importer.unresolved.items()}}
    (dest / "import-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (dest / "media-source.json").write_text(json.dumps({"unavailable": importer.asset_issues,
        "media": [{"key": k, "source": v, "local": importer.media.get(k), "appears_in": [
            {"page": p, "url": u, "placement": t} for p, u, t in sorted(importer.source_occurrences[k])
        ]} for k, v in importer.urls.items()]
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if args.strict_media and importer.asset_issues:
        raise SystemExit(1)
if __name__ == "__main__":
    main()
