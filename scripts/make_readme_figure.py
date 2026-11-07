"""The README's "results at a glance" figure, drawn from eval/m5/generator-v5/m5_analysis.json (no model call).

    .venv/bin/python scripts/make_readme_figure.py          # writes docs/figures/m5-at-a-glance-{light,dark}.svg

Standard library only, deterministic: the same analysis file gives byte-identical SVGs (a test checks that the
committed figures match). Left: the D1 2x2 as counts. Right: top-1 for every arm with its Wilson 95% interval.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "eval" / "m5" / "generator-v5" / "m5_analysis.json"
OUT = REPO / "docs" / "figures"
ARMS = (("agent_v1", "agent v1"), ("single_pass_full", "single-pass full"),
        ("single_pass_no_timeline", "single-pass, no change records"), ("rule_based", "rule-based"),
        ("keyword_only", "keyword-only"), ("latest_change", "latest-change floor"), ("alert_service", "alert-service floor"))
THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
              "axis": "#c3c2b7", "series": "#2a78d6", "border": "rgba(11,11,11,0.10)"},
    "dark": {"surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
             "axis": "#383835", "series": "#3987e5", "border": "rgba(255,255,255,0.10)"},
}
W, H = 860, 330
FONT = 'font-family="system-ui, -apple-system, Segoe UI, sans-serif"'


def text(x: float, y: float, s: str, fill: str, size: int = 12, anchor: str = "start", weight: str = "400") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


def figure(a: dict, t: dict) -> str:
    p, arms = a["primary"], a["arms"]
    both_right = arms["agent_v1"]["top1"]["k"] - p["a_right_b_wrong"]
    assert both_right == arms["single_pass_full"]["top1"]["k"] - p["b_right_a_wrong"], "inconsistent analysis file"
    both_wrong = p["n_pairs"] - both_right - p["discordant"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT} '
           f'role="img" aria-labelledby="t d">',
           '<title id="t">M5 results at a glance</title>',
           f'<desc id="d">Top-1 on 60 synthetic scenarios, one hosted model. Agent v1 right and single-pass full '
           f'wrong {p["a_right_b_wrong"]}, the reverse {p["b_right_a_wrong"]}, sign test p = {p["p_two_sided"]:.3f}. '
           + "; ".join(f'{label} {arms[k]["top1"]["k"]}/{arms[k]["top1"]["n"]}' for k, label in ARMS) + '.</desc>',
           f'<rect width="{W}" height="{H}" rx="8" fill="{t["surface"]}" stroke="{t["border"]}"/>']
    # Left: the D1 2x2
    x0, y0, cw, ch = 132, 92, 78, 52
    out += [text(24, 32, "Primary (D1): top-1 on 60 paired scenarios", t["ink"], 14, weight="600"),
            text(24, 52, "agent v1 against single-pass full", t["ink2"], 12),
            text(x0 + cw / 2, y0 - 10, "single-pass right", t["ink2"], 11, "middle"),
            text(x0 + cw * 1.5, y0 - 10, "wrong", t["ink2"], 11, "middle")]
    cells = ((0, 0, both_right, False), (1, 0, p["a_right_b_wrong"], True),
             (0, 1, p["b_right_a_wrong"], True), (1, 1, both_wrong, False))
    for col, row, n, discordant in cells:
        cx, cy = x0 + col * cw, y0 + row * ch
        out.append(f'<rect x="{cx + 1}" y="{cy + 1}" width="{cw - 2}" height="{ch - 2}" rx="4" fill="none" '
                   f'stroke="{t["series"] if discordant else t["axis"]}" stroke-width="{2 if discordant else 1}"/>')
        out.append(text(cx + cw / 2, cy + ch / 2 + 7, str(n), t["ink"], 20, "middle", "600" if discordant else "400"))
    out += [text(x0 - 10, y0 + ch / 2 + 4, "agent right", t["ink2"], 11, "end"),
            text(x0 - 10, y0 + ch * 1.5 + 4, "agent wrong", t["ink2"], 11, "end"),
            text(24, y0 + 2 * ch + 30, f'Discordant pairs (outlined): {p["a_right_b_wrong"]} against '
                                       f'{p["b_right_a_wrong"]}', t["ink"], 12),
            text(24, y0 + 2 * ch + 48, f'exact two-sided sign test, n = {p["discordant"]}, '
                                       f'p = {p["p_two_sided"]:.3f}', t["ink2"], 12)]
    # Right: top-1 with Wilson intervals
    px0, px1, py0, row_h = 520, 790, 92, 26
    out += [text(330, 32, "Top-1 with Wilson 95% interval", t["ink"], 14, weight="600"),
            text(330, 52, "60 scenarios per arm; no report counts as wrong", t["ink2"], 12)]
    for tick in (0, 25, 50, 75, 100):
        x = px0 + (px1 - px0) * tick / 100
        out.append(f'<line x1="{x:.1f}" y1="{py0 - 14}" x2="{x:.1f}" y2="{py0 + row_h * len(ARMS) - 10}" '
                   f'stroke="{t["grid"] if tick else t["axis"]}" stroke-width="1"/>')
        out.append(text(x, py0 + row_h * len(ARMS) + 6, f"{tick}%", t["muted"], 11, "middle"))
    for i, (key, label) in enumerate(ARMS):
        r = arms[key]["top1"]
        y = py0 + i * row_h
        lo, hi = (px0 + (px1 - px0) * v for v in r["wilson_95"])
        x = px0 + (px1 - px0) * r["k"] / r["n"]
        tip = escape(f'{label}: {r["k"]}/{r["n"]}, Wilson 95% [{r["wilson_95"][0]:.2f}, {r["wilson_95"][1]:.2f}]')
        out += [text(px0 - 12, y + 4, label, t["ink2"], 12, "end"),
                f'<g><title>{tip}</title>'
                f'<line x1="{lo:.1f}" y1="{y}" x2="{hi:.1f}" y2="{y}" stroke="{t["series"]}" stroke-width="2" '
                f'stroke-linecap="round"/>'
                f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{t["series"]}" stroke="{t["surface"]}" stroke-width="2"/>'
                f'<rect x="{px0}" y="{y - row_h / 2}" width="{px1 - px0}" height="{row_h}" fill="transparent"/></g>',
                text(px1 + 10, y + 4, f'{r["k"]}/{r["n"]}', t["ink"], 12)]
    out += [text(24, H - 16, "Synthetic, author-built benchmark; one hosted model (ministral-14b-2512); agent prompt v1; "
                             "one run per arm. Not a result about agents in general.", t["muted"], 11), "</svg>"]
    return "\n".join(out) + "\n"


def render(analysis: Path = ANALYSIS) -> dict[str, str]:
    a = json.loads(analysis.read_text(encoding="utf-8"))
    return {f"m5-at-a-glance-{name}.svg": figure(a, theme) for name, theme in THEMES.items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, svg in render().items():
        (OUT / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote docs/figures/{name}")


if __name__ == "__main__":
    main()
