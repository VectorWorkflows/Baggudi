"""Screenshot the built site for design review. Not part of the site build.

    .venv/Scripts/python tools/shoot.py round-1
    .venv/Scripts/python tools/shoot.py round-1 --paths / /hi/ --widths 360 1440
    .venv/Scripts/python tools/shoot.py round-4 --query hero=b --slices 3

Serves dist/ on a spare port, then for every path and width saves viewport-sized
slices down the page plus a contact sheet, into shots/<name>/. Also reports
horizontal overflow, console errors and tap targets smaller than 44px.

Needs: pip install playwright pillow (uses the installed Edge or Chrome).
"""
import argparse
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEIGHTS = {360: 740, 390: 844, 768: 1024, 1440: 900}

AUDIT = """() => {
  const small = [];
  for (const el of document.querySelectorAll('a, button, input, select, textarea, summary')) {
    let box = el.getBoundingClientRect();
    if (el.matches('input[type=radio], input[type=checkbox]') && el.parentElement) box = el.parentElement.getBoundingClientRect();
    if (!box.width || !box.height) continue;
    const inline = el.tagName === 'A' && getComputedStyle(el).display === 'inline' && el.closest('p, dd, li, figcaption');
    if (inline) continue;
    if (box.width < 43.5 || box.height < 43.5) {
      small.push(`${el.tagName.toLowerCase()}.${el.className || ''} "${(el.textContent || '').trim().slice(0, 24)}" ${Math.round(box.width)}x${Math.round(box.height)}`);
    }
  }
  const doc = document.documentElement;
  const wide = [];
  if (doc.scrollWidth > doc.clientWidth) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.right > doc.clientWidth + 1 && !el.closest('.teacher-list')) wide.push(`${el.tagName.toLowerCase()}.${el.className} right=${Math.round(r.right)}`);
    }
  }
  return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, height: doc.scrollHeight, small, wide: wide.slice(0, 8) };
}"""


def launch(p):
    for channel in ("msedge", "chrome", None):
        try:
            return p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        except Exception:
            continue
    sys.exit("No browser found for Playwright.")


def sheet(files, dest, per_row):
    images = [Image.open(f) for f in files]
    w, h = images[0].size
    rows = (len(images) + per_row - 1) // per_row
    gap = 24
    canvas = Image.new("RGB", (per_row * w + (per_row + 1) * gap, rows * h + (rows + 1) * gap), "#8a8f9c")
    for i, im in enumerate(images):
        canvas.paste(im, (gap + (i % per_row) * (w + gap), gap + (i // per_row) * (h + gap)))
    canvas.save(dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--paths", nargs="+", default=["/"])
    parser.add_argument("--widths", nargs="+", type=int, default=[360, 390, 768, 1440])
    parser.add_argument("--motion", action="store_true", help="leave animations on (marks are caught mid-draw)")
    parser.add_argument("--query", default="", help="query string to add to every path, e.g. hero=b")
    parser.add_argument("--slices", type=int, default=0, help="only the first N screens of each page")
    args = parser.parse_args()

    out = ROOT / "shots" / args.name
    out.mkdir(parents=True, exist_ok=True)
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    PORT = probe.getsockname()[1]
    probe.close()
    server = subprocess.Popen([sys.executable, str(ROOT / "serve.py"), "--port", str(PORT)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            sys.exit("serve.py did not start.")
        with sync_playwright() as p:
            browser = launch(p)
            for path in args.paths:
                tag = path.strip("/").replace("/", "-") or "home"
                if args.query:
                    tag += "-" + args.query.replace("=", "-")
                for width in args.widths:
                    height = HEIGHTS.get(width, 900)
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=2 if width < 768 else 1,
                        reduced_motion="no-preference" if args.motion else "reduce",
                        is_mobile=width < 768, has_touch=width < 768,
                    )
                    page = context.new_page()
                    errors = []
                    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(f"http://127.0.0.1:{PORT}{path}" + (f"?{args.query}" if args.query else ""), wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    info = page.evaluate(AUDIT)
                    files = []
                    step = height - (120 if width < 768 else 80)
                    count = (info["height"] + step - 1) // step
                    if args.slices:
                        count = min(count, args.slices)
                    for i in range(count):
                        page.evaluate(f"window.scrollTo(0, {i * step})")
                        page.wait_for_timeout(120 if not args.motion else 900)
                        f = out / f"{tag}-{width}-{i + 1:02d}.png"
                        page.screenshot(path=str(f))
                        files.append(f)
                    per_row = 5 if width < 768 else (3 if width == 768 else 2)
                    per_sheet = per_row * (1 if width < 768 else 2)
                    for n in range(0, len(files), per_sheet):
                        sheet(files[n:n + per_sheet], out / f"sheet-{tag}-{width}-{n // per_sheet + 1}.png", per_row)
                    overflow = "OVERFLOW" if info["scrollWidth"] > info["clientWidth"] else "no overflow"
                    print(f"{path} @ {width}: {info['height']}px tall, {count} slices, {overflow}")
                    for w in info["wide"]:
                        print("    wide:", w)
                    for s in info["small"]:
                        print("    small target:", s)
                    for err in errors:
                        print("    console error:", err)
                    context.close()
            browser.close()
    finally:
        server.terminate()
    print("Saved to", out)


if __name__ == "__main__":
    main()
