"""Scripted, repeatable recording of the local viewer for the README: dev runs 3 (right) and 12 (wrong) on the M4
page, with captions. Dev data only; no model, no key, no network beyond 127.0.0.1.

Run with the recording tools, which live outside the project's requirements (Playwright drives the installed
Google Chrome; Pillow assembles the GIF):

    ~/tools/recording-venv/bin/python scripts/record_demo.py

It starts the viewer with the project's venv on a free local port, takes one screenshot per caption, and writes
docs/figures/demo.gif and docs/figures/demo-still.png. Before each screenshot it scans the page text for scenario
IDs outside the dev manifest, home-folder paths, held-out or fresh-split markers and key-like strings, and stops
if any appear. (Dataframes are drawn on a canvas that a text scan can't see; review the frames by eye too.)
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "figures"
FRAMES = REPO / "docs" / "figures" / "demo-frames"  # kept out of git (see .gitignore); for review only
RUN = "generator-v5/mistral-ministral-14b-2512"  # the M4 core runs, dev split
VIEWPORT = {"width": 1280, "height": 800}
WIDTH = 960  # GIF width
HOME = str(Path.home())
DEV_IDS = set(json.loads((REPO / "eval" / "manifests" / "dev.json").read_text())["scenario_ids"])
FORBIDDEN = [re.compile(re.escape(HOME)), re.compile(r"/Users/|/home/"), re.compile(r"heldout|held-out data", re.I),
             re.compile(r"m5-fresh|m5fresh"), re.compile(r"sk-[A-Za-z0-9]{16,}|_API_KEY=\S")]

# (trace, heading to scroll to, caption, seconds on screen)
SHOTS = [
    ("03-sc-3e3ceb314e.jsonl", "Agent runs",
     "The viewer replays committed agent traces on dev data. Run: the M4 core runs (dev). Trace: run 3.", 4.0),
    ("03-sc-3e3ceb314e.jsonl", "States in order",
     "Dev run 3 · a memory leak in payments. The agent moves TRIAGE → GATHER → HYPOTHESIZE → VERIFY → REPORT.", 5.0),
    ("03-sc-3e3ceb314e.jsonl", "Hypotheses re-ranking",
     "It ranks payments / memory_leak first, citing the memory alert and the log lines it gathered. Right.", 5.0),
    ("03-sc-3e3ceb314e.jsonl", "Claims and their source records",
     "Every claim in the report links to the record it cites.", 4.0),
    ("12-sc-91404ea5fc.jsonl", "Hypotheses re-ranking",
     "Dev run 12 · the real cause is a config change that cut auth's database pool. The agent ranks "
     "pool exhaustion first, with high confidence. Wrong.", 6.0),
    ("12-sc-91404ea5fc.jsonl", "Tool calls and evidence",
     "It only searched logs and metrics. It never called a change tool, so it never saw the config change.", 6.0),
]
END_CAPTION = ("Dev runs from the committed M4 traces · synthetic data · one hosted model (ministral-14b-2512). "
               "The full evaluation is in the README.")

CSS = """
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
#demo-caption { position: fixed; right: 0; bottom: 0; z-index: 100000; padding: 14px 28px;
  background: rgba(11, 11, 11, 0.86); color: #ffffff; font: 600 19px/1.4 system-ui, -apple-system, sans-serif; }
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_viewer(port: int) -> subprocess.Popen:
    proc = subprocess.Popen([str(REPO / ".venv" / "bin" / "streamlit"), "run", "app/viewer.py", "--server.port",
                             str(port), "--server.address", "127.0.0.1", "--server.headless", "true",
                             "--browser.gatherUsageStats", "false"],
                            cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise SystemExit("the viewer did not start")


def choose(page: Page, label: str, option: str) -> None:
    page.evaluate("() => document.getElementById('demo-caption')?.remove()")  # the caption bar can cover the list
    box = page.get_by_role("combobox", name=label)
    box.scroll_into_view_if_needed()
    box.click()
    box.fill(option)  # typing filters the list, which avoids clicking while the page is still rerunning
    page.get_by_role("option", name=option, exact=True).click()
    page.wait_for_timeout(2500)
    if box.input_value() != option:
        raise SystemExit(f"could not select {option!r} in {label!r}")


def check_text(page: Page, where: str) -> None:
    text = page.inner_text("body")
    for pattern in FORBIDDEN:
        if pattern.search(text):
            raise SystemExit(f"{where}: forbidden text on screen ({pattern.pattern}); nothing written")
    foreign = {i for i in re.findall(r"sc-[0-9a-f]{10}", text)} - DEV_IDS
    if foreign:
        raise SystemExit(f"{where}: {len(foreign)} scenario ID(s) outside the dev manifest on screen; nothing written")


def caption(page: Page, text: str) -> None:
    page.evaluate("""t => { let c = document.getElementById('demo-caption');
        if (!c) { c = document.createElement('div'); c.id = 'demo-caption'; document.body.appendChild(c); }
        const sb = document.querySelector('[data-testid="stSidebar"]');
        c.style.left = (sb ? sb.getBoundingClientRect().right : 0) + 'px';  // start where the sidebar ends
        c.textContent = t; }""", text)


def scroll_to(page: Page, heading: str) -> None:
    page.locator("h1, h2, h3").filter(has_text=heading).first.evaluate(
        "h => { const m = h.closest('[data-testid=\"stMain\"]') || document.scrollingElement;"
        " h.scrollIntoView({block: 'start'}); window.scrollBy(0, -24); }")
    page.wait_for_timeout(800)


def record() -> list[tuple[Path, float]]:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("*.png"):
        old.unlink()
    port = free_port()
    viewer = start_viewer(port)
    shots: list[tuple[Path, float]] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1, color_scheme="light")
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.get_by_role("link", name="M4 · Agent runs").click()
            page.wait_for_selector("h1:has-text('Agent runs')")
            page.add_style_tag(content=CSS)
            choose(page, "Run", RUN)
            current = None
            for i, (trace, heading, text, seconds) in enumerate(SHOTS, 1):
                if trace != current:
                    choose(page, "Trace", trace)
                    page.add_style_tag(content=CSS)
                    current = trace
                scroll_to(page, heading)
                check_text(page, f"frame {i}")
                caption(page, text)
                path = FRAMES / f"{i:02d}.png"
                page.screenshot(path=str(path))
                shots.append((path, seconds))
            caption(page, END_CAPTION)
            path = FRAMES / f"{len(SHOTS) + 1:02d}.png"
            check_text(page, "end frame")
            page.screenshot(path=str(path))
            shots.append((path, 4.0))
            browser.close()
    finally:
        viewer.terminate()
        viewer.wait(timeout=10)
    return shots


def assemble(shots: list[tuple[Path, float]]) -> None:
    frames = []
    for path, _ in shots:
        im = Image.open(path).convert("RGB")
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.Resampling.LANCZOS)
        frames.append(im.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    frames[0].save(OUT / "demo.gif", save_all=True, append_images=frames[1:], loop=0, optimize=True,
                   duration=[int(s * 1000) for _, s in shots], disposal=1)
    still = Image.open(shots[4][0]).convert("RGB")  # run 12's ranking: the failure, in one image
    still.resize((WIDTH, round(still.height * WIDTH / still.width)), Image.Resampling.LANCZOS).save(
        OUT / "demo-still.png", optimize=True)


def main() -> int:
    if not (REPO / "data" / "dev" / "scenarios").is_dir():
        print("generate the dev split first: .venv/bin/python -m sentinelops.simulator --split dev", file=sys.stderr)
        return 2
    os.environ.pop("MISTRAL_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    shots = record()
    assemble(shots)
    total = sum(s for _, s in shots)
    print(f"wrote docs/figures/demo.gif ({(OUT / 'demo.gif').stat().st_size / 1e6:.2f} MB, {len(shots)} frames, "
          f"{total:.0f} s) and docs/figures/demo-still.png; frames for review in docs/figures/demo-frames/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
