"""Home page. Every section returns "" when it has nothing real (or, in the
draft, nothing sample) to show, so production only carries confirmed facts."""
import re
from urllib.parse import urlencode

from .core import caret, circle, e, icon, join_words, photo, pick, plain, tick
from .layout import jsonld_organisation, page

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat"]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def class_map(ctx):
    return {c["id"]: c for c in ctx.centre["classes"]}


def classes_label(ctx, ids, lang=None):
    """'Class 8', 'Classes 6 and 7', 'Commerce'."""
    lang = lang or ctx.lang
    by_id = class_map(ctx)
    if len(ids) == 1:
        return pick(by_id[ids[0]]["label"], lang)
    shorts = [pick(by_id[i]["short"], lang) for i in ids]
    word = ctx._string("finder.classes_word", lang, {})
    return f"{word} {join_words(shorts, ctx._string('finder.and', lang, {}))}"


def days_label(ctx, days, lang=None):
    lang = lang or ctx.lang
    return ", ".join(ctx._string(f"days.{d}", lang, {}) for d in days)


def batch_summary(ctx, batch, lang=None):
    lang = lang or ctx.lang
    return (
        f"{classes_label(ctx, batch['classes'], lang)}, {pick(batch['subject'], lang)}, "
        f"{days_label(ctx, batch['days'], lang)}, {ctx.time_range(batch, lang)}"
    )


def more_link(href, label, external=False):
    rel = ' rel="noopener"' if external else ""
    return f'<a class="more" href="{e(href)}"{rel}><span>{label}</span>{icon("arrow")}</a>'


# ---- hero -------------------------------------------------------------------

def trust_line(ctx):
    """Real numbers only; each one is a chip until it is confirmed."""
    trust = []
    year = ctx.fact("year_started")
    trust.append(ctx.t("hero.since", year=year) if year else ctx.chip("hero.confirm_year", "centre", "the year the centre started"))
    size = ctx.fact("batch_size")
    trust.append(ctx.t("hero.batch_size", n=size) if size else ctx.chip("hero.confirm_batch_size", "classes", "the largest batch size"))
    rating = ctx.fact("google_rating")
    trust.append(ctx.t("hero.rating", rating=rating) if rating else ctx.chip("hero.confirm_rating", "centre", "the Google rating and number of reviews"))
    trust = [item for item in trust if item]
    if not trust:
        return ""
    return '<ul class="hero__trust">' + "".join(f"<li>{item}</li>" for item in trust) + "</ul>"


def hero_parts(ctx):
    """The name for screen readers, the red margin note and the single, quiet action."""
    spoken_name = f'<span class="sr">{ctx.tx(ctx.centre["name"])}. </span>'
    note = f'<p class="hero__note margin-note">{tick()}<span>{ctx.t("hero.note")}</span></p>'
    action = more_link(ctx.url("demo/"), ctx.t("cta.demo"))
    return spoken_name, note, action


def hero(ctx, trust):
    """'The corrected line': a line written on the ruled page, with the
    teacher's caret adding what was left out."""
    spoken_name, note, action = hero_parts(ctx)
    return f"""
<section class="hero" aria-labelledby="hero-title">
  <h1 id="hero-title">{spoken_name}{ctx.rich("hero.title")}{caret()}</h1>
  <p class="hero__insert">{ctx.t("hero.insert")}</p>
  <p class="hero__place">{ctx.t("hero.place")}</p>
  <div class="hero__cta">
    {note}
    {action}
  </div>
  {trust}
</section>"""


# ---- find your batch --------------------------------------------------------

def batch_card(ctx, batch, is_sample, default_class):
    subject = pick(batch["subject"], ctx.lang)
    on = batch["classes"]
    off = "" if default_class in on else " data-off"
    strip = "".join(
        f'<span class="{"is-on" if d in batch["days"] else ""}">{ctx.t("day_letters." + d)}</span>' for d in DAYS
    )
    teacher = ctx.tx(batch["teacher"]) if batch.get("teacher") else ctx.chip(
        "finder.confirm_teacher", "classes", "the teacher for each batch"
    )
    teacher_row = f'<div><dt>{ctx.t("finder.teacher")}</dt><dd>{teacher}</dd></div>' if teacher else ""

    seats = batch.get("seats_left")
    summary = batch_summary(ctx, batch)
    if seats:
        text = ctx.t("finder.seats_one") if seats == 1 else ctx.t("finder.seats_many", n=seats)
        seats_html = f'<p class="batch__seats">{tick()}<span>{text}</span></p>'
        query = urlencode({
            "batch": batch["id"],
            "class": default_class if default_class in on else on[0],
            "subject": pick(batch["subject"], "en"),
            "when": f"{days_label(ctx, batch['days'], 'en')}, {ctx.time_range(batch, 'en')}",
        })
        action = (
            f'<a class="btn btn--card" data-demo-link href="{e(ctx.url("demo/") + "?" + query)}">'
            f'<span>{ctx.t("finder.book")}</span>{icon("arrow")}</a>'
        )
    else:
        seats_html = f'<p class="batch__seats batch__seats--none"><span>{ctx.t("finder.seats_none")}</span></p>'
        wa = ctx.wa(ctx.s("whatsapp.batch", batch=summary))
        action = (
            f'<a class="btn btn--card btn--card-quiet" href="{e(wa)}" rel="noopener">'
            f'{icon("whatsapp")}<span>{ctx.t("finder.ask")}</span></a>'
        ) if wa else ""
    return f"""
    <li class="batch" data-classes="{e(" ".join(on))}" data-subject="{e(slug(pick(batch["subject"], "en")))}"{off}>
      {ctx.stamp() if is_sample else ""}
      <h3 class="batch__subject">{e(subject)}</h3>
      <p class="batch__for">{e(classes_label(ctx, on))}</p>
      <div class="daystrip" aria-hidden="true">{strip}</div>
      <p class="batch__time"><span class="batch__clock">{e(ctx.time_range(batch))}</span> <span class="batch__days">{e(days_label(ctx, batch["days"]))}</span></p>
      <dl class="batch__meta">{teacher_row}</dl>
      {seats_html}
      {action}
    </li>"""


def finder(ctx):
    batches, is_sample = ctx.collection("batches", "classes", lambda b: "batch: " + batch_summary(ctx, b, "en"))
    if not batches:
        return ""
    classes = ctx.centre["classes"]
    default_class = classes[0]["id"]

    class_opts = []
    for c in classes:
        checked = " checked" if c["id"] == default_class else ""
        numeric = c["id"].isdigit()
        prefix = f'<span class="sr">{ctx.t("finder.class_word")} </span>' if numeric else ""
        wide = "" if numeric else " classpick__opt--word"
        class_opts.append(
            f'<label class="classpick__opt{wide}"><input type="radio" name="class" value="{e(c["id"])}" '
            f'data-label="{ctx.tx(c["label"])}"{checked}><span>{prefix}{ctx.tx(c["short"])}</span></label>'
        )

    # One option per subject that has a batch, tagged with the classes it applies to.
    subjects = {}
    for b in batches:
        key = slug(pick(b["subject"], "en"))
        entry = subjects.setdefault(key, {"label": b["subject"], "classes": []})
        entry["classes"] += [c for c in b["classes"] if c not in entry["classes"]]
    # A class with a single subject shows just that subject, already chosen;
    # "All" only appears when there is something to choose between.
    for_default = [key for key, entry in subjects.items() if default_class in entry["classes"]]
    only = for_default[0] if len(for_default) == 1 else None
    subject_opts = [
        f'<label class="chipopt" data-all{" data-off" if only else ""}><input type="radio" name="subject" value=""'
        f'{"" if only else " checked"}><span>{ctx.t("finder.all")}</span></label>'
    ]
    for key, entry in subjects.items():
        off = "" if default_class in entry["classes"] else " data-off"
        subject_opts.append(
            f'<label class="chipopt" data-classes="{e(" ".join(entry["classes"]))}"{off}>'
            f'<input type="radio" name="subject" value="{e(key)}"{" checked" if key == only else ""}>'
            f'<span>{ctx.tx(entry["label"])}</span></label>'
        )

    # Unconfirmed class facts surface beside the subject step for that class.
    notes = []
    for c in classes:
        chip = ""
        if c["id"] == "commerce":
            if not c.get("for_classes"):
                chip = ctx.chip("finder.confirm_commerce_classes", "classes")
        elif not c.get("subjects"):
            chip = ctx.chip("finder.confirm_subjects", "classes", "subjects for " + pick(c["label"], "en"), cls=ctx.pick(c["label"]))
        if chip:
            off = "" if c["id"] == default_class else " data-off"
            notes.append(f'<p class="finder__note" data-classes="{e(c["id"])}"{off}>{chip}</p>')

    cards = "".join(batch_card(ctx, b, is_sample, default_class) for b in batches)
    wa = ctx.wa(ctx.s("whatsapp.general"))
    empty_link = f' <a href="{e(wa)}" rel="noopener">{ctx.t("cta.whatsapp")}</a>' if wa else ""
    return f"""
<section class="finder" id="batches" aria-labelledby="finder-title" data-finder>
  <h2 id="finder-title">{ctx.t("finder.title")}</h2>
  <fieldset class="finder__step">
    <legend>{ctx.t("finder.step_class")}</legend>
    <div class="classpick">{"".join(class_opts)}</div>
  </fieldset>
  <fieldset class="finder__step">
    <legend>{ctx.t("finder.step_subject")}</legend>
    <div class="chipopts">{"".join(subject_opts)}</div>
    {"".join(notes)}
  </fieldset>
  <p class="sr" aria-live="polite" data-finder-status data-one="{ctx.t("finder.count_one")}" data-many="{ctx.t("finder.count_many")}"></p>
  <ul class="batches" role="list">{cards}</ul>
  <p class="finder__empty" data-finder-empty hidden>{ctx.t("finder.empty")}{empty_link}</p>
</section>"""


# ---- why parents choose us --------------------------------------------------

def why(ctx):
    items, is_sample = ctx.collection("practices", "centre", lambda p: "practice: " + plain(pick(p["title"], "en")))
    if not items:
        return ""
    rows = "".join(
        f"""
    <li class="practice">
      {tick("practice__tick")}
      <h3 class="practice__title">{ctx.rich_value(p["title"])}</h3>
      <p class="practice__detail">{ctx.tx(p["detail"])}</p>
      {ctx.stamp() if is_sample else ""}
    </li>"""
        for p in items
    )
    return f"""
<section class="section why" aria-labelledby="why-title">
  <h2 id="why-title">{ctx.t("why.title")}</h2>
  <ul class="practices" role="list">{rows}</ul>
</section>"""


# ---- a week here ------------------------------------------------------------

def week(ctx):
    data = ctx.fact("week")
    is_sample = False
    if not data:
        ctx.need("classes", "Sample to replace: the weekly timetable (class slots, weekly test, doubt hour, monthly parent meeting)")
        if not ctx.draft:
            return ""
        data, is_sample = ctx.sample["week"], True

    days, rows, kinds = data["days"], data["rows"], data["kinds"]
    head = "".join(f'<th scope="col">{ctx.t("days." + d)}</th>' for d in days)
    # Slots that repeat across days or down the afternoon merge into one block,
    # the way they are drawn on a wall timetable.
    grid = [row["cells"] for row in rows]
    covered = set()
    body = []
    for r, row in enumerate(rows):
        cells = [f'<th scope="row">{e(row["time"])}</th>']
        for col, kind in enumerate(grid[r]):
            if (r, col) in covered:
                continue
            if kind == "none":
                cells.append('<td class="tt tt--none"></td>')
                continue
            free = lambda rr, cc: grid[rr][cc] == kind and (rr, cc) not in covered
            across = 1
            while col + across < len(days) and free(r, col + across):
                across += 1
            down = 1
            while r + down < len(rows) and all(free(r + down, col + i) for i in range(across)):
                down += 1
            covered.update((r + j, col + i) for j in range(down) for i in range(across))
            spans = (f' colspan="{across}"' if across > 1 else "") + (f' rowspan="{down}"' if down > 1 else "")
            long = ctx.tx(kinds[kind]["long"])
            if across >= 3:  # room for the full label at any width
                label, block = long, " tt--block"
            else:
                label = f'<span class="tt__short" aria-hidden="true">{ctx.tx(kinds[kind]["short"])}</span><span class="tt__long">{long}</span>'
                block = ""
            if kind == "test":
                label = circle(label)
            cells.append(f'<td class="tt tt--{e(kind)}{block}"{spans}>{label}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    notes = "".join(f"<li>{ctx.tx(n)}</li>" for n in data.get("notes", []))
    link = more_link(ctx.url("classes/"), ctx.t("week.link")) if ctx.pages["classes"]["live"] else ""
    return f"""
<section class="section week" aria-labelledby="week-title">
  <div class="week__intro">
    <h2 id="week-title">{ctx.t("week.title")}</h2>
    <ul class="week__notes" role="list">{notes}</ul>
  </div>
  <div class="week__table">
    {ctx.stamp() if is_sample else ""}
    <table class="timetable">
      <caption class="sr">{ctx.t("week.caption")}</caption>
      <thead><tr><th scope="col">{ctx.t("week.time")}</th>{head}</tr></thead>
      <tbody>{"".join(body)}</tbody>
    </table>
  </div>
  {link}
</section>"""


# ---- teachers ---------------------------------------------------------------

def teacher_cards(ctx):
    """Named people from centre.json first, then sample teachers in the draft."""
    cards = []
    for person in ctx.centre.get("people") or []:
        if not ctx.draft and not person.get("role"):
            continue  # a bare name is not enough to publish
        person_name = person["name"]
        known, missing = [], []
        checks = [
            ("role", "teacher__role", lambda v: ctx.tx(v), f"{person_name}'s role at the centre"),
            ("subjects", "teacher__facts", lambda v: ctx.tx(v), f"the subjects {person_name} teaches"),
            ("years", "teacher__role", lambda v: ctx.t("teachers.years", n=v), f"how many years {person_name} has taught"),
            ("approach", "teacher__approach", lambda v: ctx.tx(v), f"one line on how {person_name} teaches"),
        ]
        for field, cls, show, note in checks:
            if person.get(field):
                known.append(f'<p class="{cls}">{show(person[field])}</p>')
            else:
                ctx.need("teachers", "To confirm: " + note)
                missing.append(ctx.s("teachers.confirm_" + field))
        chip = ""
        if missing and ctx.draft:
            chip = f'<p class="chip">{ctx.t("draft.chip")}: {e(", ".join(missing))}</p>'
        cards.append(f"""
    <li class="teacher">
      {photo(ctx, "teacher", photo_id="teacher-" + person["id"], name=person_name)}
      <div class="teacher__body">
        <h3 class="teacher__name">{ctx.proper(person_name)}</h3>
        {"".join(known)}
        {chip}
      </div>
    </li>""")

    samples, is_sample = ctx.collection(
        "teachers", "teachers",
        lambda t: f"teacher: {pick(t['role_label'], 'en')} ({pick(t['subjects'], 'en')})")
    for t in samples:
        role = ctx.pick(t["role_label"])
        teacher_name = ctx.tx(t["name"]) if t.get("name") else ctx.chip("teachers.confirm_name", "teachers", "the name of each teacher")
        cards.append(f"""
    <li class="teacher">
      {photo(ctx, "teacher", photo_id="teacher-" + t["id"], name=role)}
      <div class="teacher__body">
        {ctx.stamp() if is_sample else ""}
        <h3 class="teacher__name">{e(role)}</h3>
        <p class="teacher__role">{teacher_name}</p>
        <p class="teacher__facts">{ctx.tx(t["subjects"])} <span class="teacher__years">{ctx.t("teachers.years", n=t["years"])}</span></p>
        <p class="teacher__approach">{ctx.tx(t["approach"])}</p>
      </div>
    </li>""")
    return cards


def teachers(ctx):
    cards = teacher_cards(ctx)
    if not cards:
        return ""
    link = ""
    if ctx.pages["about"]["live"]:
        link = f'<p class="section__more">{more_link(ctx.url("about/") + "#teachers", ctx.t("teachers.link"))}</p>'
    return f"""
<section class="section teachers" aria-labelledby="teachers-title">
  <h2 id="teachers-title">{ctx.t("teachers.title")}</h2>
  <ul class="teacher-list" role="list">{"".join(cards)}</ul>
  {link}
</section>"""


# ---- progress ---------------------------------------------------------------

def report_card(ctx, story, is_sample):
    head = "".join(f'<th scope="col">{ctx.tx(col)}</th>' for col in story["columns"])
    rows = []
    for row in story["rows"]:
        marks = []
        for i, mark in enumerate(row["marks"]):
            value = e(mark)
            marks.append(f"<td>{circle(value) if row.get('circle') == i else value}</td>")
        rows.append(f'<tr><th scope="row">{ctx.tx(row["subject"])}</th>{"".join(marks)}</tr>')
    return f"""
    <li class="report">
      {ctx.stamp() if is_sample else ""}
      <p class="report__kind">{ctx.t("progress.card_title")}</p>
      <h3 class="report__who">{ctx.tx(story["student"])}<span>{ctx.tx(story["class_label"])}</span></h3>
      <table class="report__table">
        <thead><tr><th scope="col">{ctx.t("progress.subject")}</th>{head}</tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <p class="report__outof">{ctx.tx(story["out_of"])}</p>
      <p class="report__remark"><span class="report__remark-label">{ctx.t("progress.remarks")}</span> {ctx.tx(story["remark"])}</p>
    </li>"""


def progress(ctx, limit=2):
    stories, is_sample = ctx.collection(
        "progress", "teachers",
        lambda s: f"progress story: {pick(s['student'], 'en')}, {pick(s['class_label'], 'en')}")
    if not stories:
        return ""
    cards = "".join(report_card(ctx, s, is_sample) for s in stories[:limit])
    return f"""
<section class="section progress" aria-labelledby="progress-title">
  <div class="progress__intro">
    <h2 id="progress-title">{ctx.t("progress.title")}</h2>
    <p>{ctx.t("progress.intro")}</p>
  </div>
  <ul class="reports" role="list">{cards}</ul>
</section>"""


# ---- what parents say -------------------------------------------------------

def reviews(ctx):
    items, is_sample = ctx.collection("reviews", "centre", lambda r: "review: " + pick(r["text"], "en"))
    if not items:
        return ""
    quotes = "".join(
        f"""
    <li class="review">
      <figure>
        <blockquote><p>{ctx.tx(r["text"])}</p></blockquote>
        <figcaption>{ctx.tx(r["by"])} {ctx.stamp() if is_sample else ""}</figcaption>
      </figure>
    </li>"""
        for r in items
    )
    rating = ctx.fact("google_rating")
    rating_html = ctx.t("reviews.rating", rating=rating) if rating else ctx.chip("reviews.confirm_rating", "centre", "the Google rating and number of reviews")
    maps = ctx.fact("maps_url")
    link = more_link(maps, ctx.t("reviews.link"), external=True) if maps else ""
    foot = f'<p class="reviews__foot">{rating_html} {link}</p>' if (rating_html or link) else ""
    return f"""
<section class="section reviews" aria-labelledby="reviews-title">
  <h2 id="reviews-title">{ctx.t("reviews.title")}</h2>
  <ul class="review-list" role="list">{quotes}</ul>
  {foot}
</section>"""


# ---- the centre -------------------------------------------------------------

def centre_photos(ctx):
    shots = [photo(ctx, "classroom", cls="gallery__main"), photo(ctx, "board"), photo(ctx, "notebook")]
    shots = [s for s in shots if s]
    if not shots:
        return ""
    return f"""
<section class="section centre" aria-labelledby="centre-title">
  <h2 id="centre-title">{ctx.t("centre.title")}</h2>
  <div class="gallery">{"".join(shots)}</div>
</section>"""


# ---- fees and admission -----------------------------------------------------

def fee_rows(ctx):
    """(rows, is_sample) for the fee table, honouring the single display setting."""
    if ctx.centre["fees"]["display"] == "ask":
        return [], False
    real = ctx.fact("fees", "rows")
    if real:
        return real, False
    rows = ctx.sample["fees"]["rows"]
    for row in rows:
        ctx.need("fees", f"Sample to replace: fee for {pick(row['group'], 'en')} ({pick(row['what'], 'en')}), shown as from ₹{row['from']:,} a month")
    return (rows, True) if ctx.draft else ([], False)


def fees(ctx):
    steps, steps_sample = ctx.collection(
        "admission_steps", "fees",
        lambda s: f"admission step: {pick(s['title'], 'en')} ({pick(s['detail'], 'en')})")
    rows, rows_sample = fee_rows(ctx)
    display = ctx.centre["fees"]["display"]
    setting_chip = ctx.chip("fees.confirm_display", "fees")

    steps_html = ""
    if steps:
        items = "".join(
            f"""
      <li class="step">
        <h4 class="step__title">{ctx.tx(s["title"])} {ctx.stamp() if steps_sample else ""}</h4>
        <p>{ctx.tx(s["detail"])}</p>
      </li>"""
            for s in steps
        )
        steps_html = f"""
  <div class="fees__steps">
    <h3>{ctx.t("fees.steps_title")}</h3>
    <ol class="steps">{items}</ol>
  </div>"""

    fees_html = ""
    if display == "ask":
        fees_html = f"""
  <div class="fees__table">
    <h3>{ctx.t("fees.fees_title")}</h3>
    <p>{ctx.t("fees.ask")}</p>
    {f'<p class="fees__setting">{setting_chip}</p>' if setting_chip else ""}
  </div>"""
    elif rows:
        before, after = (part.strip() for part in ctx.t("fees.from_amount").split("{amount}"))
        before = f'<span class="fee__from">{before}</span> ' if before else ""
        after = f' <span class="fee__from">{after}</span>' if after else ""
        body = "".join(
            f"""
        <tr>
          <th scope="row">{ctx.tx(r["group"])}<span>{ctx.tx(r["what"])}</span></th>
          <td>{before}<span class="fee__amount">₹{r["from"]:,}</span>{after}{' ' + ctx.stamp() if rows_sample else ""}</td>
        </tr>"""
            for r in rows
        )
        fees_html = f"""
  <div class="fees__table">
    <h3>{ctx.t("fees.fees_title")}</h3>
    <table class="feetable"><tbody>{body}</tbody></table>
    {f'<p class="fees__setting">{setting_chip}</p>' if setting_chip else ""}
  </div>"""

    if not steps_html and not fees_html:
        return ""
    link = ""
    if ctx.pages["admissions"]["live"]:
        link = f'<p class="section__more">{more_link(ctx.url("admissions/"), ctx.t("fees.link"))}</p>'
    return f"""
<section class="section fees" aria-labelledby="fees-title">
  <h2 id="fees-title">{ctx.t("fees.title")}</h2>
  <div class="fees__grid">{steps_html}{fees_html}
  </div>
  {link}
</section>"""


# ---- faq --------------------------------------------------------------------

def faq(ctx):
    items, is_sample = ctx.collection("faq", "centre", lambda f: "FAQ answer: " + pick(f["q"], "en") + " " + pick(f["a"], "en"))
    if not items:
        return ""
    rows = "".join(
        f"""
      <div class="qa">
        <dt>{ctx.tx(f["q"])}</dt>
        <dd>{ctx.tx(f["a"])} {ctx.stamp() if is_sample else ""}</dd>
      </div>"""
        for f in items
    )
    wa = ctx.wa(ctx.s("whatsapp.question"))
    aside = ""
    if wa:
        aside = f"""
  <p class="faq__ask margin-note"><span>{ctx.t("faq.ask_note")}</span> {more_link(wa, ctx.t("faq.ask_link"), external=True)}</p>"""
    return f"""
<section class="section faq" aria-labelledby="faq-title">
  <div class="sheet">
    <h2 id="faq-title">{ctx.t("faq.title")}</h2>
    <dl class="qa-list">{rows}
    </dl>
  </div>{aside}
</section>"""


# ---- find us ----------------------------------------------------------------

def find_us(ctx):
    c = ctx.centre
    address = "<br>".join(e(line) for line in c["address"]["lines"])
    directions = ctx.fact("landmark_directions")
    directions_html = ctx.tx(directions) if directions else ctx.chip("find.confirm_directions", "location")
    hours = ctx.fact("hours")
    hours_html = ctx.tx(hours) if hours else ctx.chip("find.confirm_hours", "location")
    rows = [f'<div><dt>{ctx.t("find.address")}</dt><dd><address{ctx.foreign()}>{address}</address></dd></div>']
    if directions_html:
        rows.append(f'<div><dt>{ctx.t("find.directions")}</dt><dd>{directions_html}</dd></div>')
    if hours_html:
        rows.append(f'<div><dt>{ctx.t("find.hours")}</dt><dd>{hours_html}</dd></div>')
    if ctx.fact("phone", "tel"):
        rows.append(
            f'<div><dt>{ctx.t("find.phone")}</dt><dd><a href="tel:{e(c["phone"]["tel"])}">{e(c["phone"]["display"])}</a></dd></div>'
        )
    maps = ctx.fact("maps_url")
    maps_btn = ""
    if maps:
        maps_btn = f'<a class="btn btn--ghost" href="{e(maps)}" rel="noopener">{icon("pin")}<span>{ctx.t("cta.maps")}</span></a>'
    return f"""
<section class="section find" id="find-us" aria-labelledby="find-title">
  <div class="find__text">
    <h2 id="find-title">{ctx.t("find.title")}</h2>
    <dl class="facts">{"".join(rows)}</dl>
    {maps_btn}
  </div>
  {photo(ctx, "entrance", cls="find__photo")}
</section>"""


# ---- closing ----------------------------------------------------------------

def closing(ctx):
    wa = ctx.wa(ctx.s("whatsapp.general"))
    wa_btn = ""
    if wa:
        wa_btn = f'<a class="btn btn--ghost" href="{e(wa)}" rel="noopener">{icon("whatsapp")}<span>{ctx.t("cta.whatsapp")}</span></a>'
    return f"""
<section class="closing" aria-labelledby="closing-title">
  <h2 id="closing-title">{ctx.rich("closing.line")}</h2>
  <div class="closing__actions">
    <a class="btn btn--primary" href="{e(ctx.url("demo/"))}"><span>{ctx.t("cta.demo")}</span>{icon("arrow")}</a>
    {wa_btn}
  </div>
</section>"""


def render(ctx):
    trust = trust_line(ctx)
    batch_finder = finder(ctx)
    lone = "" if batch_finder else " opening--lone"
    body = f"""
<div class="opening{lone}">
{hero(ctx, trust)}
{batch_finder}
</div>
{why(ctx)}
{week(ctx)}
{teachers(ctx)}
{progress(ctx)}
{reviews(ctx)}
{centre_photos(ctx)}
{fees(ctx)}
{faq(ctx)}
{find_us(ctx)}
{closing(ctx)}"""
    return page(
        ctx,
        title=ctx.t("meta.home_title"),
        description=ctx.t("meta.home_description"),
        body=body,
        jsonld=jsonld_organisation(ctx),
    )
