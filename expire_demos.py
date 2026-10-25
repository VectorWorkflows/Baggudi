#!/usr/bin/env python3
"""Takes down the demos whose time is up, and puts one back with a single command.

    python expire_demos.py --expire-old              every demo sent 35 or more days ago with no answer: expired, committed, pushed
    python expire_demos.py --expire-old --dry-run    which ones it would expire; changes nothing
    python expire_demos.py --expire-old --days 45    another window
    python expire_demos.py --restore some-slug       that demo back as it was, committed, pushed

The dates come from Lead Hunter's database (table leads), which this only reads. A lead counts from its Date Sent once
its Status is sent, never from the day its demo was made. A lead still unsent, or one that has answered (any Response
but none or Pending), never expires.

Expiring moves <slug>/index.html to .archive/<slug>/index.html and writes the expired page in its place. .archive/
stays on this machine (.gitignore): committed, GitHub Pages would serve it. If it is ever missing, --restore takes the
page from the git history instead. The expired page loads /tracker.js with data-expired="1", so a visit sends Sam an
urgent Telegram alert with the restore command in it. The demo's other pages are left as they are.
"""
import argparse
import datetime as dt
import html
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
DB = Path(r"C:\Users\Sameer Bhardwaj\Desktop\Lead Hunter\leadhunter.db")
ARCHIVE = SITE / ".archive"
DAYS = 35
# a Response that is no answer yet
WAITING = {"", "none", "pending"}
MARK = 'data-expired="1"'


def sent_leads(db: Path) -> list[dict]:
    """Every sent lead with a demo: its slug, name, Date Sent and Response."""
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT outreach_id, name, slug, sent_date, reply_status FROM leads WHERE status = 'sent' AND slug != ''").fetchall()
    finally:
        con.close()
    leads = []
    for oid, name, slug, sent, reply in rows:
        try:
            sent = dt.date.fromisoformat((sent or "").strip())
        except ValueError:
            sent = None
        # the database holds the demo's address, baggudi.com/<slug>
        leads.append({"id": oid, "name": name or "", "slug": (slug or "").strip().rstrip("/").rsplit("/", 1)[-1], "sent": sent, "reply": (reply or "").strip()})
    return leads


def business_name(page: str, fallback: str) -> str:
    """The name the demo itself shows, from its <script id="biz">; else the Google name up to its first ' - ' or ' | '."""
    found = re.search(r'<script type="application/json" id="biz">(.*?)</script>', page, re.S)
    if found:
        try:
            return json.loads(found.group(1)).get("businessName") or fallback
        except ValueError:
            pass
    return re.split(r"\s[-|–]\s", fallback)[0].strip()


def expired_page(name: str, days: int) -> str:
    name = html.escape(name)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0B0B0F">
<title>Preview expired · Vector Workflows</title>
<link rel="icon" href="/portal/img/favicon.ico" sizes="any">
<link rel="preconnect" href="https://vectorworkflows.com" crossorigin>
<style>
@font-face {{ font-family: "GT Sectra Display"; src: url("https://vectorworkflows.com/assets/fonts/GT-Sectra-Display/400-Regular/font.woff2") format("woff2"); font-display: swap; }}
@font-face {{ font-family: "GT Sectra Display"; font-style: italic; src: url("https://vectorworkflows.com/assets/fonts/GT-Sectra-Display/400-Regular-Italic/font.woff2") format("woff2"); font-display: swap; }}
@font-face {{ font-family: "ABC Whyte Inktrap"; font-weight: 500; src: url("https://vectorworkflows.com/assets/fonts/ABC-Whyte-Inktrap/500-Medium/font.woff2") format("woff2"); font-display: swap; }}
@font-face {{ font-family: "ABC Whyte"; src: url("https://vectorworkflows.com/assets/fonts/ABC-Whyte/400-Regular/font.woff2") format("woff2"); font-display: swap; }}
@font-face {{ font-family: "GT America Mono"; src: url("https://vectorworkflows.com/assets/fonts/GT-America-Mono/400-Regular/font.woff2") format("woff2"); font-display: swap; }}
:root {{
  color-scheme: dark;
  --ground: #0B0B0F; --raised: #111116; --bone: #EDE8E0; --bone-2: #AFAAA3; --bone-3: #928D86;
  --violet: #6756B9; --violet-deep: #5746A0; --lilac: #BCB4F4;
  --edge: color-mix(in oklch, var(--bone) 10%, transparent);
  --display: "GT Sectra Display", Georgia, "Times New Roman", serif;
  --ui: "ABC Whyte Inktrap", system-ui, -apple-system, "Segoe UI", sans-serif;
  --body: "ABC Whyte", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "GT America Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; min-height: 100%; }}
body {{
  min-height: 100svh; display: flex; flex-direction: column; padding: clamp(20px, 4vw, 40px);
  background: radial-gradient(120% 70% at 50% -10%, color-mix(in oklch, var(--violet) 22%, transparent), transparent 60%), var(--ground);
  color: var(--bone); font: 400 1.0625rem/1.6 var(--body); -webkit-font-smoothing: antialiased;
}}
.brand {{ display: inline-flex; align-items: center; gap: 12px; color: var(--bone); text-decoration: none; font: 500 1rem/1 var(--ui); letter-spacing: -0.01em; }}
.brand img {{ display: block; }}
main {{ flex: 1; display: grid; place-items: center; padding: 48px 0; }}
.card {{
  width: min(100%, 560px); padding: clamp(28px, 6vw, 48px); border: 1px solid var(--edge); border-radius: 20px;
  background: color-mix(in oklch, var(--raised) 80%, transparent); box-shadow: inset 0 1px 0 color-mix(in oklch, var(--bone) 12%, transparent), 0 40px 80px -40px color-mix(in oklch, var(--violet) 35%, transparent);
}}
.label {{ display: inline-flex; align-items: center; gap: 8px; margin: 0 0 20px; color: var(--lilac); font: 400 0.75rem/1 var(--mono); letter-spacing: 0.08em; text-transform: uppercase; }}
.label::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--lilac); box-shadow: 0 0 12px var(--lilac); }}
h1 {{ margin: 0 0 16px; font: 400 clamp(2rem, 1.5rem + 2.4vw, 3rem)/1.08 var(--display); letter-spacing: -0.01em; text-wrap: balance; }}
h1 em {{ color: var(--lilac); }}
p {{ margin: 0 0 14px; color: var(--bone-2); text-wrap: pretty; }}
.actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }}
.btn {{ display: inline-flex; align-items: center; min-height: 48px; padding: 0 22px; border-radius: 999px; font: 500 0.9375rem/1 var(--ui); text-decoration: none; }}
.btn-solid {{ background: var(--violet); color: var(--bone); }}
.btn-solid:hover {{ background: var(--violet-deep); }}
.btn:focus-visible {{ outline: 2px solid var(--lilac); outline-offset: 3px; }}
footer {{ color: var(--bone-3); font: 400 0.75rem/1.4 var(--mono); letter-spacing: 0.04em; }}
</style>
<script src="/tracker.js" defer {MARK}></script>
</head>
<body>
<header><a class="brand" href="https://vectorworkflows.com/"><img src="/portal/img/mark-56.webp" srcset="/portal/img/mark-28.webp 1x, /portal/img/mark-56.webp 2x, /portal/img/mark-84.webp 3x" width="39" height="28" alt="">Vector Workflows</a></header>
<main>
  <div class="card">
    <p class="label">Preview expired</p>
    <h1>This preview for <em>{name}</em> has been taken down.</h1>
    <p>Previews stay online for {days} days after they're sent, and this one has run its course.</p>
    <p>It can be back up the same day: just reply to Sam's email, or get in touch.</p>
    <div class="actions"><a class="btn btn-solid" href="https://vectorworkflows.com/">Get in touch</a></div>
  </div>
</main>
<footer>© Vector Workflows</footer>
</body>
</html>
"""


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=SITE, capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{done.stderr.strip()}")
    return done.stdout


def publish(paths: list[str], message: str, body: str = "") -> None:
    """Commits exactly these files, whatever else is waiting in the repo, and pushes."""
    git("add", "--", *paths)
    git("commit", "-m", message, *(["-m", body] if body else []), "--", *paths)
    git("push")
    print(f"Committed and pushed: {message}. Live on baggudi.com in about a minute.")


def expire_old(db: Path, days: int, dry_run: bool) -> None:
    today = dt.date.today()
    due = []
    for lead in sorted(sent_leads(db), key=lambda lead: (lead["sent"] or today, lead["slug"])):
        page = SITE / lead["slug"] / "index.html"
        if lead["reply"].lower() not in WAITING or lead["sent"] is None or today < lead["sent"] + dt.timedelta(days=days):
            continue
        if not page.exists():
            print(f"  #{lead['id']} {lead['slug']}: no {lead['slug']}/index.html here, skipped")
            continue
        if MARK in page.read_text(encoding="utf-8"):
            continue
        due.append(lead)
    if not due:
        print(f"Nothing to expire: no demo sent {days} or more days ago is still waiting for an answer.")
        return
    for lead in due:
        print(f"  #{lead['id']} {lead['slug']}: sent {lead['sent']:%d %b}, {(today - lead['sent']).days} days ago, Response {lead['reply'] or 'none'}")
    if dry_run:
        print(f"{len(due)} to expire. Nothing was changed (--dry-run).")
        return
    changed = []
    for lead in due:
        page, kept = SITE / lead["slug"] / "index.html", ARCHIVE / lead["slug"] / "index.html"
        original = page.read_bytes()
        kept.parent.mkdir(parents=True, exist_ok=True)
        kept.write_bytes(original)
        page.write_bytes(expired_page(business_name(original.decode("utf-8"), lead["name"]), days).encode("utf-8"))
        changed.append(f"{lead['slug']}/index.html")
    publish(changed, f"Expire {len(due)} demo{'s' if len(due) > 1 else ''} sent {days}+ days ago", "\n".join(lead["slug"] for lead in due))


def from_history(slug: str) -> bytes | None:
    """The newest committed <slug>/index.html that is not the expired page."""
    rel = f"{slug}/index.html"
    for commit in git("log", "--format=%H", "--", rel).split():
        shown = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=SITE, capture_output=True)
        if shown.returncode == 0 and MARK.encode() not in shown.stdout:
            return shown.stdout
    return None


def restore(slug: str) -> None:
    if not re.fullmatch(r"[\w-]+", slug):
        sys.exit(f"{slug!r} is not a slug: letters, digits, hyphens and underscores only.")
    page, kept = SITE / slug / "index.html", ARCHIVE / slug / "index.html"
    if page.exists() and MARK not in page.read_text(encoding="utf-8"):
        sys.exit(f"{slug} is not expired: {slug}/index.html is the demo already.")
    original = kept.read_bytes() if kept.exists() else from_history(slug)
    if original is None:
        sys.exit(f"No copy of {slug}/index.html to restore: not in .archive/ and not in the git history.")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_bytes(original)
    publish([f"{slug}/index.html"], f"Restore the {slug} demo")
    if kept.exists():
        kept.unlink()
        kept.parent.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--expire-old", action="store_true", help=f"expire every demo sent DAYS or more days ago that has no answer (default {DAYS})")
    action.add_argument("--restore", metavar="SLUG", help="put SLUG's demo back, commit and push")
    parser.add_argument("--days", type=int, default=DAYS, help=f"days after Date Sent (default {DAYS})")
    parser.add_argument("--dry-run", action="store_true", help="with --expire-old: list what it would expire, change nothing")
    parser.add_argument("--db", type=Path, default=DB, help="Lead Hunter's database, if not the usual one")
    args = parser.parse_args()
    if args.restore:
        restore(args.restore)
    else:
        if not args.db.exists():
            sys.exit(f"No database at {args.db}. Pass --db PATH.")
        expire_old(args.db, args.days, args.dry_run)


if __name__ == "__main__":
    main()
