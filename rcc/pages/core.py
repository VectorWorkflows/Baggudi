"""Shared rendering helpers: the build context, text lookup, the draft-mode
chip and stamp, red-pen marks, icons and photo placeholders."""
import html
import re
from urllib.parse import quote

# Checklist topics for notes/TO-CONFIRM.md, in the order they are written.
TOPICS = [
    ("centre", "The centre"),
    ("classes", "Classes and batches"),
    ("fees", "Fees and payment"),
    ("teachers", "Teachers and results"),
    ("location", "Location and contact"),
    ("photos", "Photos"),
]

LANGS = ["en", "hi"]
LANG_LABELS = {"en": "EN", "hi": "हिं"}


def e(text):
    return html.escape(str(text), quote=True)


MARKERS = re.compile(r"\[\[|\]\]|==")


def plain(text):
    """Text without the [[underline]] and ==highlight== markers."""
    return MARKERS.sub("", text)


def pick(value, lang):
    """Text in the given language from an {en, hi} pair; hi falls back to en."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or ""
    return "" if value is None else str(value)


class Ctx:
    """Everything a page needs to render itself in one language and mode."""

    def __init__(self, *, lang, draft, base, centre, sample, strings, assets, needs, pages):
        self.lang = lang
        self.draft = draft
        self.base = base
        self.centre = centre
        self.sample = sample
        self.strings = strings
        self.assets = assets
        self.needs = needs
        self.pages = pages
        self.slug = ""

    # ---- text -----------------------------------------------------------
    def pick(self, value):
        return pick(value, self.lang)

    def tx(self, value):
        return e(self.pick(value))

    def _string(self, key, lang, fmt):
        node = self.strings
        for part in key.split("."):
            node = node[part]
        text = pick(node, lang)
        return text.format(**fmt) if fmt else text

    def s(self, key, **fmt):
        return self._string(key, self.lang, fmt)

    def t(self, key, **fmt):
        return e(self.s(key, **fmt))

    def rich(self, key):
        """Escaped interface string with its [[underline]] and ==highlight== marks drawn."""
        return marked(self.t(key))

    def rich_value(self, value):
        """The same, for an {en, hi} pair from the data files."""
        return marked(self.tx(value))

    def proper(self, text):
        """A proper name: plain in English, marked as English on a Hindi page."""
        return e(text) if self.lang == "en" else name(text)

    def foreign(self):
        """The lang attribute for content that stays in English on a Hindi page."""
        return "" if self.lang == "en" else ' lang="en"'

    def time_range(self, batch, lang=None):
        """'3:30–4:30 pm' in English, the Hindi wording in Hindi."""
        return self._string("time." + batch.get("period", "pm"), lang or self.lang,
                            {"start": batch["start"], "end": batch["end"]})

    # ---- urls -----------------------------------------------------------
    def url(self, slug="", lang=None):
        lang = lang or self.lang
        return self.base + ("" if lang == "en" else lang + "/") + slug

    def asset(self, path):
        return f"{self.base}assets/{path}?v={self.assets[path]}"

    def wa(self, message):
        number = self.fact("phone", "whatsapp")
        return f"https://wa.me/{number}?text={quote(message)}" if number else ""

    # ---- facts, chips, samples -----------------------------------------
    def fact(self, *path):
        """A confirmed value from centre.json, or None while it is unconfirmed."""
        node = self.centre
        for part in path:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return None if node in (None, "", [], {}) else node

    def need(self, topic, text):
        """Record a line for notes/TO-CONFIRM.md (once, from the English pass)."""
        if self.lang == "en" and text not in self.needs[topic]:
            self.needs[topic].append(text)

    def chip(self, key, topic, note=None, **fmt):
        """Dashed 'to confirm: <what>' chip. Empty in production."""
        what_en = self._string(key, "en", fmt)
        self.need(topic, "To confirm: " + (note or what_en))
        if not self.draft:
            return ""
        return f'<span class="chip">{self.t("draft.chip")}: {e(self.s(key, **fmt))}</span>'

    def stamp(self):
        return f'<span class="stamp">{self.t("draft.stamp")}</span>' if self.draft else ""

    def collection(self, key, topic, describe):
        """Items for a section: confirmed ones from centre.json, otherwise the
        samples (draft only). Returns (items, is_sample)."""
        real = self.fact(key)
        if real:
            return real, False
        items = self.sample.get(key) or []
        for item in items:
            self.need(topic, "Sample to replace: " + describe(item))
        return (items, True) if self.draft else ([], False)


# ---- red-pen marks --------------------------------------------------------
# Each path is drawn by hand: slightly uneven, never closed or symmetric.
# pathLength="1" lets one CSS rule draw any of them.

def _mark(kind, viewbox, d, extra=""):
    return (
        f'<svg class="mark mark--{kind}{extra}" viewBox="{viewbox}" preserveAspectRatio="none" '
        f'aria-hidden="true" focusable="false"><path pathLength="1" d="{d}"/></svg>'
    )


UNDERLINE_PATH = "M2 7.4C24 5.6 43 8.3 67 6.9S117 5.2 142 6.5 180 7.6 198 5.4"
TICK_PATH = "M2.5 11.6C5 13.4 7 15.8 8.7 18.2 11.4 11.2 15.8 5.6 21.8 1.8"
CIRCLE_PATH = (
    "M23 5.6C10 6.4 3.6 13.6 4 22.4 4.5 32.8 17 39.4 33 38.9 "
    "49 38.3 60.2 31 59.6 20.4 59 10 46 4 30 4.7 24 5 18.4 6.3 14.2 8.8"
)


def underline(inner, static=False):
    extra = " mark--static" if static else ""
    return f'<span class="u">{inner}{_mark("underline", "0 0 200 12", UNDERLINE_PATH, extra)}</span>'


CARET_PATH = "M2.4 14.6C5.2 10.4 7.8 6.3 10 2.2 12.5 6.5 15 10.6 17.7 14.3"


def caret():
    """The mark a teacher makes where something has to be added."""
    return _mark("caret", "0 0 20 17", CARET_PATH)


def highlight(inner):
    return f'<mark class="hl">{inner}</mark>'


def marked(escaped):
    """Turn the markers in an already-escaped string into drawn marks."""
    def underlined(m):
        # Keep a comma or full stop with the underlined words, never alone on the next line.
        mark, after = underline(m.group(1)), m.group(2)
        return f'<span class="nb">{mark}{after}</span>' if after else mark

    escaped = re.sub(r"\[\[(.+?)\]\]([,.;:!?\u0964]?)", underlined, escaped)
    return re.sub(r"==(.+?)==", lambda m: highlight(m.group(1)), escaped)


def name(text):
    """A proper name kept in its own script on a Hindi page."""
    return f'<span lang="en">{e(text)}</span>'


def tick(cls=""):
    return _mark("tick", "0 0 24 20", TICK_PATH, f" {cls}" if cls else "")


def circle(inner):
    return f'<span class="circled">{inner}{_mark("circle", "0 0 64 44", CIRCLE_PATH)}</span>'


# ---- icons: one 1.5px stroke, drawn for this site -------------------------
ICONS = {
    "phone": '<path d="M6.6 3.5h2.7l1.5 4-2 1.4a12 12 0 0 0 6.3 6.3l1.4-2 4 1.5v2.7a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z"/>',
    "whatsapp": '<path d="M12 3.3a8.7 8.7 0 0 0-7.5 13.1l-1.2 4.3 4.4-1.2A8.7 8.7 0 1 0 12 3.3z"/><path d="M9.3 8.2c-.5 1 .1 2.8 1.6 4.3s3.3 2.1 4.3 1.6l.5-1.3-1.7-.9-.8.7c-.7-.3-1.5-1.1-1.8-1.8l.7-.8-.9-1.7z"/>',
    "arrow": '<path d="M4.5 12h15M13.5 6l6 6-6 6"/>',
    "pin": '<path d="M12 21s-6.5-5.9-6.5-11a6.5 6.5 0 0 1 13 0c0 5.1-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    "menu": '<path d="M4 8.5h16M4 15.5h16"/>',
}


def icon(name):
    return (
        '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'
    )


# ---- photos ---------------------------------------------------------------

def photo(ctx, slot, photo_id=None, cls="", **fmt):
    """A real photo if centre.json has one for this id, otherwise (draft only)
    a paper-framed placeholder naming the shot that is needed."""
    photo_id = photo_id or slot
    spec = ctx.strings["photos"][slot]
    ratio = "photo--" + spec["ratio"].replace(" ", "").replace("/", "x")
    extra = f" {cls}" if cls else ""
    real = ctx.fact("photos", photo_id)
    if real:
        return (
            f'<figure class="photo {ratio}{extra}"><img src="{e(ctx.base + real["src"])}" alt="{ctx.tx(real.get("alt"))}" '
            f'width="{e(real["width"])}" height="{e(real["height"])}" loading="lazy" decoding="async"></figure>'
        )
    ctx.need("photos", "Photo needed: " + ctx._string(f"photos.{slot}.label", "en", fmt))
    if not ctx.draft:
        return ""
    return (
        f'<figure class="photo photo--empty {ratio}{extra}"><div class="photo__frame"><figcaption class="photo__label">'
        f'<span class="photo__tag">{ctx.t("draft.photo")}</span> {ctx.t(f"photos.{slot}.label", **fmt)}'
        "</figcaption></div></figure>"
    )


def join_words(items, conj):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]
