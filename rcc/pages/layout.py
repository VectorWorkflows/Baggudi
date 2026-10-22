"""The page shell shared by every page: head, header, footer, phone action bar."""
import json

from .core import LANG_LABELS, LANGS, e, icon, underline

# Where each nav item appears. Results and Parents' Corner are only listed
# when the build has something to put on them.
HEADER_NAV = ["classes", "admissions", "about", "visit"]
MENU_NAV = ["home", "classes", "admissions", "demo", "about", "visit", "results", "parents"]
FOOTER_NAV = ["classes", "admissions", "demo", "about", "visit", "results", "parents", "privacy"]

THEME_COLOR = "#f8f2e4"
FONT_FILES = ["fonts/tiro-devanagari-hindi-400.woff2", "fonts/mukta-400.woff2", "fonts/mukta-600.woff2"]


def wordmark(ctx, cls=""):
    first = ctx.tx(ctx.centre["name_parts"]["first"])
    rest = ctx.tx(ctx.centre["name_parts"]["rest"])
    extra = f" {cls}" if cls else ""
    return (
        f'<a class="wordmark{extra}" href="{e(ctx.url())}" aria-label="{ctx.t("a11y.home_link")}">'
        f'<span class="wordmark__first">{underline(first, static=True)}</span>'
        f'<span class="wordmark__rest">{rest}</span></a>'
    )


def nav_items(ctx, keys, wide=None):
    """Links for the given pages. With `wide`, pages outside it are marked so
    the desktop header can leave them to the phone menu."""
    out = []
    for key in keys:
        page = ctx.pages.get(key)
        if not page or not page["live"]:
            continue
        current = ' aria-current="page"' if page["slug"] == ctx.slug else ""
        cls = ' class="site-nav__extra"' if wide is not None and key not in wide else ""
        out.append(f'<li{cls}><a href="{e(ctx.url(page["slug"]))}"{current}>{ctx.t("nav." + key)}</a></li>')
    return "".join(out)


def lang_switch(ctx):
    links = []
    for lang in LANGS:
        current = ' aria-current="true"' if lang == ctx.lang else ""
        links.append(
            f'<a href="{e(ctx.url(ctx.slug, lang))}" lang="{lang}" hreflang="{lang}"{current}>{LANG_LABELS[lang]}</a>'
        )
    return f'<div class="lang" role="group" aria-label="{ctx.t("a11y.language")}">{"".join(links)}</div>'


def header(ctx):
    tel = ctx.fact("phone", "tel")
    call = ""
    if tel:
        label = ctx.t("a11y.call_number", phone=ctx.centre["phone"]["display"])
        call = (
            f'<a class="btn btn--quiet btn--call" href="tel:{e(tel)}" aria-label="{label}">'
            f'{icon("phone")}<span>{ctx.t("cta.call")}</span></a>'
        )
    return f"""
<header class="site-header">
  {wordmark(ctx)}
  <nav class="site-nav" id="site-nav" aria-label="{ctx.t("a11y.main_nav")}">
    <ul>{nav_items(ctx, MENU_NAV, wide=HEADER_NAV)}</ul>
  </nav>
  <div class="site-header__tools">
    {lang_switch(ctx)}
    <a class="btn btn--primary btn--demo" href="{e(ctx.url("demo/"))}">{ctx.t("cta.demo_short")}</a>
    {call}
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav">
      {icon("menu")}<span>{ctx.t("a11y.menu")}</span>
    </button>
  </div>
</header>"""


def footer(ctx):
    address = "<br>".join(e(line) for line in ctx.centre["address"]["lines"])
    tel = ctx.fact("phone", "tel")
    phone = ""
    if tel:
        phone = f'<p><a href="tel:{e(tel)}">{e(ctx.centre["phone"]["display"])}</a></p>'
    hours = ctx.fact("hours")
    hours_html = ctx.tx(hours) if hours else ctx.chip("footer.confirm_hours", "location")
    hours_block = f'<p class="site-footer__hours">{hours_html}</p>' if hours_html else ""
    return f"""
<footer class="site-footer">
  <div class="site-footer__brand">
    {wordmark(ctx)}
    <address{ctx.foreign()}>{address}</address>
    {phone}
    {hours_block}
  </div>
  <nav class="site-footer__nav" aria-label="{ctx.t("a11y.footer_nav")}">
    <ul>{nav_items(ctx, FOOTER_NAV)}</ul>
  </nav>
  <p class="site-footer__credit">{ctx.t("footer.by")} <a href="https://vectorworkflows.com" rel="noopener"{ctx.foreign()}>Vector Workflows</a></p>
</footer>"""


def actionbar(ctx):
    """Phone-only sticky bar. Each action drops out if its data is missing."""
    items = []
    tel = ctx.fact("phone", "tel")
    if tel:
        items.append(f'<a class="actionbar__item" href="tel:{e(tel)}">{icon("phone")}<span>{ctx.t("cta.call")}</span></a>')
    wa = ctx.wa(ctx.s("whatsapp.general"))
    if wa:
        items.append(
            f'<a class="actionbar__item" href="{e(wa)}" rel="noopener">{icon("whatsapp")}<span>{ctx.t("cta.whatsapp_short")}</span></a>'
        )
    if ctx.pages["demo"]["live"]:
        items.append(
            f'<a class="actionbar__item actionbar__item--primary" href="{e(ctx.url("demo/"))}"><span>{ctx.t("cta.demo_short")}</span></a>'
        )
    if not items:
        return ""
    return f'<nav class="actionbar" aria-label="{ctx.t("a11y.quick_actions")}">{"".join(items)}</nav>'


def jsonld_organisation(ctx):
    """EducationalOrganization + LocalBusiness, from confirmed facts only."""
    c = ctx.centre
    data = {
        "@context": "https://schema.org",
        "@type": ["EducationalOrganization", "LocalBusiness"],
        "name": c["name"]["en"],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": c["address"]["street"],
            "addressLocality": c["address"]["locality"],
            "addressRegion": c["address"]["region"],
            "postalCode": c["address"]["postal_code"],
            "addressCountry": c["address"]["country"],
        },
        "areaServed": c["area"]["en"],
    }
    if ctx.fact("phone", "tel"):
        data["telephone"] = c["phone"]["tel"]
    if ctx.fact("maps_url"):
        data["hasMap"] = c["maps_url"]
    if ctx.fact("site_url"):
        data["url"] = c["site_url"].rstrip("/") + ctx.url()
    rating, count = ctx.fact("google_rating"), ctx.fact("google_review_count")
    if rating and count:
        data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": rating, "reviewCount": count}
    return data


def page(ctx, *, title, description, body, jsonld=None, noindex=False):
    site = ctx.fact("site_url")
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{title}</title>",
        f'<meta name="description" content="{description}">',
    ]
    if ctx.draft or noindex:
        head.append('<meta name="robots" content="noindex, nofollow">')
    head += [
        f'<meta name="theme-color" content="{THEME_COLOR}">',
        '<meta name="color-scheme" content="light">',
        '<meta name="format-detection" content="telephone=no">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:locale" content="{"hi_IN" if ctx.lang == "hi" else "en_IN"}">',
    ]
    if site and not noindex:
        root = site.rstrip("/")
        head.append(f'<link rel="canonical" href="{e(root + ctx.url(ctx.slug))}">')
        for lang in LANGS:
            head.append(f'<link rel="alternate" hreflang="{lang}" href="{e(root + ctx.url(ctx.slug, lang))}">')
    for font in FONT_FILES:
        head.append(f'<link rel="preload" href="{e(ctx.asset(font))}" as="font" type="font/woff2" crossorigin>')
    head += [
        f'<link rel="stylesheet" href="{e(ctx.asset("css/site.css"))}">',
        f'<link rel="icon" href="{e(ctx.asset("img/favicon.svg"))}" type="image/svg+xml">',
        "<script>document.documentElement.classList.add('js')</script>",
        f'<script src="{e(ctx.asset("js/site.js"))}" defer></script>',
    ]
    if jsonld:
        payload = json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")
        head.append(f'<script type="application/ld+json">{payload}</script>')
    head_html = "\n".join(head)
    return f"""<!doctype html>
<html lang="{ctx.lang}">
<head>
{head_html}
</head>
<body>
<a class="skip" href="#main">{ctx.t("a11y.skip")}</a>
<div class="page">
{header(ctx)}
<main id="main">
{body}
</main>
{footer(ctx)}
</div>
{actionbar(ctx)}
</body>
</html>
"""
