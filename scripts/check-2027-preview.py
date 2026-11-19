#!/usr/bin/env python3
"""Check the unpublished 2027 build and its separation from the public archive."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROUTE = "/agriculture-vision-2027"
TITLE = (
    "The 8th International Workshop on Agriculture-Vision: Challenges & "
    "Opportunities for Computer Vision in Agriculture"
)
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("parity", ROOT / "scripts/check-parity.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


class Preview(parity.Page):
    def __init__(self, markup):
        self.robots = []
        self.h1_text = []
        self.in_h1 = False
        super().__init__(markup)

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "robots":
            self.robots.append(attributes.get("content", ""))
        if tag == "h1":
            self.in_h1 = True

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag == "h1":
            self.in_h1 = False

    def handle_data(self, data):
        super().handle_data(data)
        if self.in_h1:
            self.h1_text.append(data)


def check_baseline(dist, baseline_path):
    """Allow only asset URL renames when the asset bytes are identical."""
    baseline = json.loads(baseline_path.read_text())
    current = {
        str(path.relative_to(dist)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in dist.rglob("*") if path.is_file()
    }
    renamed = {}
    for old, digest in baseline.items():
        if old not in current and old.startswith("_astro/"):
            matches = [name for name, value in current.items() if value == digest]
            assert len(matches) == 1, f"Original asset changed or missing: {old}"
            renamed[old] = matches[0]
    for old, digest in baseline.items():
        path = dist / renamed.get(old, old)
        assert path.is_file(), f"Original output missing: {old}"
        data = path.read_bytes()
        if path.suffix == ".html":
            for old_asset, new_asset in renamed.items():
                data = data.replace(f"/{new_asset}".encode(), f"/{old_asset}".encode())
        assert hashlib.sha256(data).hexdigest() == digest, f"Original output changed: {old}"
    print(f"Preserved {len(baseline)} original build files (equivalent asset URL renames allowed).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--baseline", type=Path, help="Optional JSON map of pre-change build SHA-256 hashes")
    args = parser.parse_args()
    dist = args.dist.resolve()
    preview_path = dist / ROUTE.lstrip("/") / "index.html"
    markup = preview_path.read_text()
    page = Preview(markup)
    assert not page.issues, page.issues
    assert page.landmarks["html"] == page.landmarks["main"] == page.landmarks["h1"] == 1
    assert page.has_title
    assert all(count == 1 for count in page.ids.values()), "Duplicate anchor IDs"
    assert " ".join("".join(page.h1_text).split()) == TITLE, "Submitted title changed"
    assert page.robots == ["noindex, nofollow"], "Draft must opt out of search indexing"
    assert "Spatial Intelligence in Agriculture" in markup
    assert "Acceptance pending" in markup
    assert "Confirmed invited speakers" in markup
    for name in ("Tyler Niday", "Igor Susmelj", "Gaurav Bansal", "Kenny Lee"):
        assert name in markup, f"Confirmed speaker missing: {name}"
    assert "Amy Tabb" not in markup, "Tentative speaker must not appear as confirmed"
    assert "Participation is subject to workshop acceptance." in markup
    assert "Calendar links will be available once the workshop schedule is confirmed." in markup
    assert "<astro-island" not in markup, "Pending workshop must not load a React island"
    assert "calendar.google.com" not in markup, "Pending workshop must not offer a Google Calendar action"
    assert not list((dist / ROUTE.lstrip("/")).glob("*.ics")), "Pending workshop must not emit a calendar file"
    assert "static.cloudflareinsights.com" not in markup, "Draft must not load production analytics"
    assert "openreview.net" not in markup and "mailto:" not in markup, "Keep proposal access and contact details out of the draft"

    links = {href for kind, href in page.files if kind == "link"}
    for year in range(2020, 2027):
        assert f"/agriculture-vision-{year}" in links, f"Missing archive edition: {year}"
    for kind, href in page.files:
        target = urlsplit(href)
        if target.netloc or target.scheme:
            continue
        file = parity.output_file(dist, target.path or ROUTE)
        assert file, f"Broken local {kind}: {href}"
        if target.fragment:
            target_page = parity.Page(file.read_text())
            assert target.fragment in target_page.ids, f"Missing anchor: {href}"

    for file in dist.rglob("*.html"):
        if file == preview_path:
            continue
        archive = Preview(file.read_text())
        assert not archive.robots, f"Archive indexing changed: {file}"
        assert not any(
            kind == "link" and urlsplit(href).path.rstrip("/") == ROUTE
            for kind, href in archive.files
        ), f"Unreleased page linked from archive: {file}"
    for name in ("navigation.json", "snapshot.json", "inventory.json"):
        assert ROUTE not in (ROOT / "src/content" / name).read_text(), f"Draft leaked into {name}"
    assert ROUTE not in (dist / "search-index.json").read_text(), "Draft leaked into search"
    for sitemap in dist.rglob("*sitemap*"):
        if sitemap.is_file():
            assert ROUTE not in sitemap.read_text(), f"Draft leaked into {sitemap}"
    print("2027 preview: title, pending calendar state, noindex, analytics exclusion, links, and archive/search/sitemap isolation passed.")
    if args.baseline:
        check_baseline(dist, args.baseline)


if __name__ == "__main__":
    main()
