#!/usr/bin/env python3
"""Offline structural checks for the generated Agriculture-Vision archive."""

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LOCAL = "https://astro-preview.invalid"
SOURCE_HOSTS = {"agriculture-vision.com", "www.agriculture-vision.com"}
RUNTIME = re.compile(
    r"sites\.google\.com/(?:_|_next)/|(?:www\.)?gstatic\.com/_/atari/"
    r"|google\.com/_/scs/sites-static/|gstatic\.com/sites/p/",
    re.IGNORECASE,
)
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


def route(path):
    return "/" + path.strip("/")


def srcset(value):
    # Data URIs contain commas and are not local requests.
    if not value.lower().startswith("data:"):
        for entry in value.split(","):
            words = entry.strip().split()
            if words:
                yield words[0]


class Page(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.files = []
        self.ids = Counter()
        self.landmarks = Counter()
        self.issues = []
        self.inline_scripts = []
        self.in_script = False
        self.has_title = False
        self.in_title = False
        self.feed(markup)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids[attrs["id"]] += 1
        if tag == "a" and attrs.get("name") and attrs.get("name") != attrs.get("id"):
            self.ids[attrs["name"]] += 1
        if tag in {"html", "main", "h1", "title"}:
            self.landmarks[tag] += 1
        if attrs.get("role") == "main" and tag != "main":
            self.landmarks["main"] += 1
        if tag == "html" and not attrs.get("lang", "").strip():
            self.issues.append("missing document language")
        if tag == "title":
            self.in_title = True
        if tag == "img" and "alt" not in attrs:
            self.issues.append(f"image has no alt attribute: {attrs.get('src', '')}")
        if tag == "iframe" and not attrs.get("title", "").strip():
            self.issues.append(f"iframe has no accessible title: {attrs.get('src', '')}")
        if tag in {"img", "script", "iframe", "audio", "video", "source", "track", "embed"}:
            if attrs.get("src"):
                self.files.append((tag, attrs["src"]))
        if tag == "object" and attrs.get("data"):
            self.files.append(("embed", attrs["data"]))
        if tag == "video" and attrs.get("poster"):
            self.files.append(("img", attrs["poster"]))
        if tag in {"img", "source"} and attrs.get("srcset"):
            self.files.extend(("img", url) for url in srcset(attrs["srcset"]))
        if tag in {"a", "area"} and attrs.get("href"):
            self.files.append(("link", attrs["href"]))
        if tag == "link" and attrs.get("href"):
            rel = (attrs.get("rel") or "").lower().split()
            if set(rel) & {"stylesheet", "icon", "preload", "modulepreload", "manifest"}:
                self.files.append(("asset", attrs["href"]))
        if attrs.get("style"):
            self.files.extend(("style asset", m[1]) for m in CSS_URL.findall(attrs["style"]))
        if tag == "script" and not attrs.get("src"):
            self.in_script = True

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_script:
            self.inline_scripts.append(data)
        if self.in_title and data.strip():
            self.has_title = True


def output_file(dist, path):
    """Match directory and flat variants, while excluding filesystem traversal."""
    relative = unquote(path).lstrip("/")
    file = (dist / relative).resolve()
    if not file.is_relative_to(dist):
        return None
    if file.is_file():
        return file
    candidates = [file / "index.html"]
    if file != dist and not file.suffix:
        candidates.append(file.with_suffix(".html"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def is_source_page(href):
    parts = urlsplit(href)
    return parts.hostname in SOURCE_HOSTS and Path(parts.path).suffix in {"", ".html"}


def run(dist, inventory, *, strict_fragments=False):
    entries = json.loads(inventory.read_text(encoding="utf-8"))["entries"]
    expected = {route(e["path"]) for e in entries if str(e.get("status", "200")) == "200"}
    if not expected:
        raise ValueError("Official inventory contains no successful pages.")
    errors, warnings = set(), set()
    embeds = defaultdict(set)
    assets = set()
    pages = {}
    for name in sorted(expected):
        file = output_file(dist, name)
        if file is None or file.suffix != ".html":
            errors.add(f"{name}: expected HTML output is missing")
        else:
            markup = file.read_text(encoding="utf-8")
            pages[name] = Page(markup)

    fragment_errors = set()
    for name, page in sorted(pages.items()):
        for issue in page.issues:
            # Imported artifacts may have unknown alternative text, but an alt
            # attribute and descriptive iframe title are mandatory even then.
            errors.add(f"{name}: {issue}")
        if page.landmarks["html"] != 1 or page.landmarks["main"] != 1 or not page.has_title:
            errors.add(f"{name}: expected one HTML root, one main landmark, and a nonempty title")
        if page.landmarks["h1"] != 1:
            warnings.add(f"{name}: found {page.landmarks['h1']} H1 elements (expected one)")
        for id_value, count in page.ids.items():
            if count > 1:
                errors.add(f"{name}: duplicate anchor ID {id_value!r}")
        for script in page.inline_scripts:
            if RUNTIME.search(script) or re.search(r"\b(?:atari_)?loadJs\b|_F_installCss", script):
                errors.add(f"{name}: inline Google Sites page runtime")

        for kind, href in page.files:
            if kind in {"script", "asset", "style asset"} and RUNTIME.search(href):
                errors.add(f"{name}: Google Sites runtime asset: {href}")
            if href.lower().startswith(("javascript:", "vbscript:")):
                errors.add(f"{name}: executable URI: {href}")
                continue
            if href.lower().startswith(("data:", "mailto:", "tel:", "sms:", "blob:")):
                continue
            base = LOCAL + (name.rstrip("/") + "/" if name != "/" else "/")
            try:
                target = urlsplit(urljoin(base, href))
                host = target.hostname
            except ValueError:
                errors.add(f"{name}: invalid URI: {href}")
                continue
            if host and host != urlsplit(LOCAL).hostname:
                if kind in {"iframe", "embed"}:
                    embeds[host].add(name)
                elif kind in {"img", "style asset"}:
                    warnings.add(f"{name}: {kind} still makes an external request: {href}")
                elif kind == "link" and is_source_page(href) and route(target.path) in expected:
                    warnings.add(f"{name}: archived page linked on original site: {href}")
                continue
            path = target.path or name
            file = output_file(dist, path)
            if file is None:
                errors.add(f"{name}: broken {kind}: {href}")
                continue
            if kind != "link":
                assets.add(file.relative_to(dist).as_posix())
            if target.fragment and kind == "link" and file.suffix == ".html":
                target_page = pages.get(route(path))
                if target_page is None:
                    target_page = Page(file.read_text(encoding="utf-8"))
                anchor = unquote(target.fragment)
                if anchor not in target_page.ids and not anchor.startswith(":~:text="):
                    fragment_errors.add(f"{name}: missing target anchor: {href}")

    if strict_fragments:
        errors.update(fragment_errors)
    else:
        warnings.update(fragment_errors)
    print(f"Official routes: {len(pages)}/{len(expected)}; linked local assets: {len(assets)}.")
    if embeds:
        print("External embeds (reported only, not fetched):")
        for host, routes in sorted(embeds.items()):
            print(f"  {host}: {', '.join(sorted(routes))}")
    for heading, issues in (("WARNING", warnings), ("ERROR", errors)):
        for detail in sorted(issues):
            print(f"{heading}: {detail}")
    print(f"{len(errors)} errors; {len(warnings)} warnings.")
    return int(bool(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--inventory", type=Path, default=ROOT / "src/content/inventory.json")
    parser.add_argument(
        "--strict-fragments", action="store_true", help="Fail on missing fragment IDs."
    )
    args = parser.parse_args()
    try:
        return run(args.dist.resolve(), args.inventory, strict_fragments=args.strict_fragments)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Could not read build or official route inventory: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
