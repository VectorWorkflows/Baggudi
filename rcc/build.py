#!/usr/bin/env python3
"""Build the Reliance Coaching Centre site. Python standard library only.

    python build.py --draft             first look: samples, chips, noindex
    python build.py                     production: confirmed facts only
    python build.py --base /rcc/        every URL works under a subfolder
    python build.py --out some-folder   write somewhere other than dist/

Every build also rewrites notes/TO-CONFIRM.md and notes/HINDI-TO-CHECK.md.
"""
import argparse
import gzip
import hashlib
import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

from pages import home, notfound
from pages.core import LANGS, MARKERS, TOPICS, Ctx

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
NOTES = ROOT / "notes"
MARKER = ".build.json"  # written into the output folder; serve.py reads it

# Markup that only the draft may contain.
DRAFT_MARKERS = ['class="stamp"', 'class="chip"', "photo--empty"]
# Sample strings shorter than this are too ordinary to search for ("Maths").
LEAK_MIN_LENGTH = 12
# Names that stay in Latin script on a Hindi page. People's names from
# centre.json are added to these; the address and anything else marked
# lang="en" in the markup is skipped altogether.
HINDI_EXEMPT = ["Google Maps", "Google", "WhatsApp", "Vector Workflows"]


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def normalise_base(base):
    base = "/" + base.strip("/") + "/"
    return "/" if base == "//" else base


def page_registry(centre, draft):
    """Every page of the site. `live` decides whether it is linked and built;
    `render` is set once the page exists."""
    has = lambda key: bool(centre.get(key))
    return {
        "home": {"slug": "", "live": True, "render": home.render},
        "classes": {"slug": "classes/", "live": True},
        "admissions": {"slug": "admissions/", "live": True},
        "demo": {"slug": "demo/", "live": True},
        "about": {"slug": "about/", "live": True},
        "visit": {"slug": "visit/", "live": True},
        "results": {"slug": "results/", "live": draft or has("results")},
        "parents": {"slug": "parents/", "live": draft or has("notices")},
        "privacy": {"slug": "privacy/", "live": True},
    }


def prepare_out(out):
    """Empty the output folder, but only if it is ours (or new, or empty)."""
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).exists():
            sys.exit(f"Refusing to build into {out}: it has files that this script did not put there.")
        shutil.rmtree(out)
    out.mkdir(parents=True)


def copy_assets(out):
    """Copy assets/ and return {relative path: short content hash} for cache busting."""
    hashes = {}
    for src in sorted(ASSETS.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(ASSETS).as_posix()
        dest = out / "assets" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        hashes[rel] = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
    return hashes


def sample_strings(node, found=None):
    """Every piece of sample wording long enough to be unmistakable."""
    found = set() if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if not key.startswith("_"):
                sample_strings(value, found)
    elif isinstance(node, list):
        for value in node:
            sample_strings(value, found)
    elif isinstance(node, str):
        # A marked phrase is rendered as separate pieces, so search for each piece.
        found.update(part.strip() for part in MARKERS.split(node) if len(part.strip()) >= LEAK_MIN_LENGTH)
    return found


def all_strings(node):
    """Every string in a data file, without the mark-up markers."""
    if isinstance(node, dict):
        for key, value in node.items():
            if not key.startswith("_"):
                yield from all_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_strings(value)
    elif isinstance(node, str):
        yield MARKERS.sub("", node)


def find_leaks(out, sample, confirmed=()):
    """Sample wording or draft markup in the built files. Must be empty in production.
    Wording that also occurs in the confirmed facts or the interface copy (a
    subject name, say) is not a leak."""
    known = [text for data in confirmed for text in all_strings(data)]
    needles = {n for n in sample_strings(sample) if not any(n in text for text in known)}
    needles |= {html.escape(s, quote=True) for s in needles}
    leaks = []
    for path in sorted(out.rglob("*")):
        if path.suffix not in {".html", ".xml", ".txt", ".js", ".css", ".json"} or path.name == MARKER:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(out).as_posix()
        for marker in DRAFT_MARKERS:
            if marker in text:
                leaks.append(f"{rel}: draft markup {marker}")
        for needle in needles:
            if needle in text:
                leaks.append(f"{rel}: sample text “{needle[:70]}”")
    return leaks


class VisibleText(HTMLParser):
    """Everything a reader of the page sees or hears: text, and the attributes
    that are shown or spoken. Anything inside lang="en" is left out."""

    SPOKEN = ("alt", "aria-label", "title", "placeholder", "data-one", "data-many", "data-label")
    VOID = {"meta", "link", "br", "input", "img", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skipping = []
        self.found = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        skip = bool(self.skipping and self.skipping[-1]) or tag in ("script", "style") or attrs.get("lang") == "en"
        if tag not in self.VOID:
            self.skipping.append(skip)
        if skip:
            return
        self.found += [attrs[name] for name in self.SPOKEN if attrs.get(name)]
        if tag == "meta" and (attrs.get("name") == "description" or attrs.get("property") in ("og:title", "og:description")):
            self.found.append(attrs.get("content") or "")

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.skipping:
            self.skipping.pop()

    def handle_data(self, data):
        if not (self.skipping and self.skipping[-1]):
            self.found.append(data)


def find_english(out, centre):
    """English left showing on the Hindi pages. Must be empty in every build."""
    exempt = HINDI_EXEMPT + [person["name"] for person in centre.get("people") or []]
    exempt.sort(key=len, reverse=True)
    problems = []
    for path in sorted((out / "hi").rglob("*.html")):
        reader = VisibleText()
        reader.feed(path.read_text(encoding="utf-8"))
        rel = path.relative_to(out).as_posix()
        seen = set()
        for text in reader.found:
            checked = re.sub(r"\{\w+\}", " ", text)  # {n}-style slots filled in by the page script
            for phrase in exempt:
                checked = checked.replace(phrase, " ")
            if re.search(r"[A-Za-z]{2,}", checked) and text.strip() not in seen:
                seen.add(text.strip())
                problems.append(f"{rel}: \u201c{' '.join(text.split())[:90]}\u201d")
    return problems


def write_to_confirm(needs, draft):
    lines = [
        "# To confirm",
        "",
        "Everything the website is still waiting on. Each line is either a fact shown",
        "as a dashed “to confirm” chip, a piece of sample content shown with a red",
        "“sample” stamp, or a photo that has to be taken. Confirmed facts go into",
        "`data/centre.json`; the production build shows nothing from this list.",
        "",
        f"_Written by `build.py` on every build. Last build: {'draft' if draft else 'production'}._",
    ]
    for key, title in TOPICS:
        items = needs[key]
        if not items:
            continue
        lines += ["", f"## {title}", ""]
        lines += [f"- [ ] {item}" for item in items]
    (NOTES / "TO-CONFIRM.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def hindi_rows(node, path=()):
    if isinstance(node, dict):
        if node.get("hi") and "en" in node:
            yield ".".join(path), node["en"], node["hi"]
            return
        for key, value in node.items():
            if not key.startswith("_"):
                yield from hindi_rows(value, path + (key,))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from hindi_rows(value, path + (str(i),))


def write_hindi_check(files):
    lines = [
        "# Hindi to check",
        "",
        "Every Hindi string on the site, beside its English. Fix any of them in the",
        "data file named in the heading. The build fails if a Hindi page shows English;",
        "names, phone numbers and the address are the only exceptions.",
        "",
        "_Written by `build.py` on every build._",
    ]
    for name, data in files:
        rows = list(hindi_rows(data))
        if not rows:
            continue
        lines += ["", f"## data/{name}", "", "| Where | English | Hindi | OK? |", "| --- | --- | --- | --- |"]
        for where, en, hi in rows:
            cell = lambda s: s.replace("|", "\\|")
            lines.append(f"| `{where}` | {cell(en)} | {cell(hi)} | |")
    (NOTES / "HINDI-TO-CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build the Reliance Coaching Centre site.")
    parser.add_argument("--draft", action="store_true", help="first look: sample content, to-confirm chips, noindex")
    parser.add_argument("--base", default="/", help="URL path the site is served under, e.g. /rcc/ (default /)")
    parser.add_argument("--out", default="dist", help="output folder (default dist)")
    args = parser.parse_args()

    base = normalise_base(args.base)
    out = (ROOT / args.out).resolve()  # an absolute --out replaces ROOT
    centre, strings = load("centre.json"), load("strings.json")
    # Sample content is only rendered when ctx.draft is set, and the production
    # build is searched for it afterwards (find_leaks).
    sample = load("sample.json")

    prepare_out(out)
    assets = copy_assets(out)
    pages = page_registry(centre, args.draft)
    needs = {key: [] for key, _ in TOPICS}

    def context(lang, draft, needs):
        return Ctx(lang=lang, draft=draft, base=base, centre=centre, sample=sample,
                   strings=strings, assets=assets, needs=needs, pages=pages)

    written = []
    for lang in LANGS:
        ctx = context(lang, args.draft, needs)
        for key, page in pages.items():
            if not page["live"] or "render" not in page:
                continue
            ctx.slug = page["slug"]
            dest = out / ("" if lang == "en" else lang) / page["slug"] / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(page["render"](ctx), encoding="utf-8")
            written.append(dest)

    for lang in LANGS:
        dest = out / ("" if lang == "en" else lang) / "404.html"
        dest.write_text(notfound.render(context(lang, args.draft, needs)), encoding="utf-8")
        written.append(dest)

    if not args.draft:
        # The checklist always describes the draft: render it once more, in
        # memory only, so production lists the same chips and samples.
        needs = {key: [] for key, _ in TOPICS}
        ctx = context("en", True, needs)
        for page in page_registry(centre, True).values():
            if "render" in page:
                ctx.slug = page["slug"]
                page["render"](ctx)

    site_url = centre.get("site_url")
    if not args.draft:
        robots = ["User-agent: *", "Allow: /"]
        if site_url:
            root = site_url.rstrip("/")
            urls = [
                root + base + ("" if lang == "en" else lang + "/") + page["slug"]
                for lang in LANGS for page in pages.values() if page["live"] and "render" in page
            ]
            sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
            sitemap += [f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls]
            sitemap.append("</urlset>")
            (out / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
            robots.append(f"Sitemap: {root}{base}sitemap.xml")
        else:
            print("Note: site_url is not set in data/centre.json, so sitemap.xml and canonical links were left out.")
        (out / "robots.txt").write_text("\n".join(robots) + "\n", encoding="utf-8")
    if not site_url:
        needs["centre"].append("To confirm: the website address (domain), needed for sitemap.xml and canonical links")

    (out / MARKER).write_text(json.dumps({"base": base, "draft": args.draft}), encoding="utf-8")
    NOTES.mkdir(exist_ok=True)
    write_to_confirm(needs, args.draft)
    write_hindi_check([("centre.json", centre), ("strings.json", strings), ("sample.json", sample)])

    english = find_english(out, centre)
    if english:
        print("BUILD FAILED: English is showing on the Hindi pages:", file=sys.stderr)
        for problem in english:
            print("  " + problem, file=sys.stderr)
        sys.exit(1)

    if not args.draft:
        leaks = find_leaks(out, sample, confirmed=(centre, strings))
        if leaks:
            print("BUILD FAILED: sample content leaked into the production build:", file=sys.stderr)
            for leak in leaks:
                print("  " + leak, file=sys.stderr)
            sys.exit(1)

    js = sum(len(gzip.compress(p.read_bytes())) for p in (out / "assets" / "js").glob("*.js"))
    css = sum(len(gzip.compress(p.read_bytes())) for p in (out / "assets" / "css").glob("*.css"))
    print(f"Built {'DRAFT' if args.draft else 'production'} site: {len(written)} pages into {out} (base {base})")
    print(f"  JS {js / 1024:.1f} kB gzipped, CSS {css / 1024:.1f} kB gzipped")
    print(f"  To confirm: {sum(len(v) for v in needs.values())} items in notes/TO-CONFIRM.md")


if __name__ == "__main__":
    main()
