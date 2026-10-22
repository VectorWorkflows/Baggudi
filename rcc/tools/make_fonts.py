"""One-off font preparation. Not part of the site build.

Downloads the three OFL font files from the google/fonts repository, subsets
them to Latin + Devanagari, writes woff2 into assets/fonts/, and prints the
metric overrides used for the fallback @font-face rules in assets/css/site.css.

    python tools/make_fonts.py [cache-dir]

Needs: pip install fonttools brotli
"""
import io
import sys
import tempfile
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "fonts"
RAW = "https://raw.githubusercontent.com/google/fonts/main/"

FONTS = [
    # (source path in google/fonts, output name)
    ("ofl/tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf", "tiro-devanagari-hindi-400.woff2"),
    ("ofl/mukta/Mukta-Regular.ttf", "mukta-400.woff2"),
    ("ofl/mukta/Mukta-SemiBold.ttf", "mukta-600.woff2"),
]
LICENCES = [
    ("ofl/tirodevanagarihindi/OFL.txt", "OFL-TiroDevanagariHindi.txt"),
    ("ofl/mukta/OFL.txt", "OFL-Mukta.txt"),
]
# Fallback faces to measure against: (label, local file or google/fonts path)
FALLBACKS = {
    "Georgia": Path(r"C:\Windows\Fonts\georgia.ttf"),
    "Arial": Path(r"C:\Windows\Fonts\arial.ttf"),
    "Noto Serif": "ofl/notoserif/NotoSerif[wdth,wght].ttf",
    "Roboto": "ofl/roboto/Roboto[wdth,wght].ttf",
}

UNICODES = (
    list(range(0x20, 0x7F))            # Basic Latin
    + [0xA0, 0xA9, 0xB7, 0xD7]         # nbsp, copyright, middle dot, multiply
    + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026]
    + [0x20B9]                         # rupee
    + list(range(0x900, 0x980))        # Devanagari
    + [0x200C, 0x200D, 0x25CC]         # joiners, dotted circle
)

# Devanagari shaping, kerning, marks and the numeral styles the site uses.
# Small caps, fractions, superscripts and stylistic sets are dropped for size.
FEATURES = [
    "abvs", "akhn", "blwf", "blws", "cjct", "half", "haln", "nukt", "pres",
    "psts", "rkrf", "rphf", "vatu", "locl", "ccmp", "calt", "liga", "rlig",
    "kern", "mark", "mkmk", "abvm", "blwm", "dist", "tnum", "lnum", "case",
]

# English letter frequencies (per 1000) plus space, for an average advance.
FREQ = {
    " ": 180, "e": 102, "t": 75, "a": 65, "o": 62, "i": 57, "n": 57, "s": 53,
    "r": 50, "h": 50, "l": 33, "d": 33, "u": 23, "c": 22, "m": 20, "f": 19,
    "w": 17, "g": 16, "p": 15, "y": 15, "b": 12, "v": 8, "k": 6, "x": 1,
    "j": 1, "q": 1, "z": 1,
}


def fetch(path, cache):
    target = cache / path.replace("/", "__").replace("[", "_").replace("]", "_")
    if not target.exists():
        url = RAW + urllib.request.quote(path)
        print("  fetching", url)
        target.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    return target


def avg_advance(font):
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    total = weight = 0
    for ch, w in FREQ.items():
        glyph = cmap.get(ord(ch))
        if glyph:
            total += hmtx[glyph][0] * w
            weight += w
    return total / weight / font["head"].unitsPerEm


def vertical(font):
    upm = font["head"].unitsPerEm
    os2, hhea = font["OS/2"], font["hhea"]
    if os2.fsSelection & (1 << 7):  # USE_TYPO_METRICS
        return os2.sTypoAscender / upm, -os2.sTypoDescender / upm, os2.sTypoLineGap / upm
    return hhea.ascent / upm, -hhea.descent / upm, hhea.lineGap / upm


def main():
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "rcc-fonts"
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for src, name in LICENCES:
        text = fetch(src, cache).read_text(encoding="utf-8")
        (OUT / name).write_text(text, encoding="utf-8")
        reserved = [l for l in text.splitlines() if "Reserved Font Name" in l and "with" in l.lower()]
        print(f"{name}: reserved font name line: {reserved[:1] or 'none'}")

    measured = {}
    for src, name in FONTS:
        ttf = fetch(src, cache)
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = FEATURES
        options.hinting = False
        options.desubroutinize = True
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
        options.notdef_outline = True
        font = subset.load_font(str(ttf), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=UNICODES)
        subsetter.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, options)
        (OUT / name).write_bytes(buf.getvalue())
        full = TTFont(str(ttf))
        measured[name] = (avg_advance(full), vertical(full))
        feats = sorted({f.FeatureTag for f in full["GSUB"].table.FeatureList.FeatureRecord})
        print(f"{name}: {len(buf.getvalue()) / 1024:.1f} kB, features: {' '.join(feats)}")

    print("\nFallback overrides (paste into site.css):")
    pairs = [
        ("tiro-devanagari-hindi-400.woff2", ["Georgia", "Noto Serif"]),
        ("mukta-400.woff2", ["Arial", "Roboto"]),
    ]
    for name, fallbacks in pairs:
        width, (asc, desc, gap) = measured[name]
        for label in fallbacks:
            ref = FALLBACKS[label]
            ref = TTFont(str(ref if isinstance(ref, Path) else fetch(ref, cache)))
            adjust = width / avg_advance(ref)
            print(
                f"  {name} vs {label}: size-adjust {adjust * 100:.2f}%; "
                f"ascent-override {asc / adjust * 100:.2f}%; "
                f"descent-override {desc / adjust * 100:.2f}%; "
                f"line-gap-override {gap / adjust * 100:.2f}%"
            )


if __name__ == "__main__":
    main()
