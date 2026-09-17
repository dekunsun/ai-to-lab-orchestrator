"""Build the GitHub social preview card (1280x640).

    ./.venv/bin/python docs/social/build_social_preview.py

This is what renders when the repository link is pasted into LinkedIn, Slack or
a message, so it is the first thing most people will ever see of this project.

Like the deck, it reads its figures from artifacts/ rather than carrying its own
copy — the curve is the real 30-seed median, not an illustration.

Requires playwright with a local Chrome: pip install playwright
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "social", "social_preview.png")
BENCH = os.path.join(ROOT, "artifacts", "benchmark_results", "cdte_benchmark.json")

# chart box inside the 1280x640 canvas
X0, X1, Y0, Y1 = 706, 1216, 168, 470
LO, HI = 0.18, 0.96


def polyline(curve: list[float]) -> str:
    n = len(curve)
    return " ".join(
        f"{X0 + i / (n - 1) * (X1 - X0):.1f},{Y1 - (v - LO) / (HI - LO) * (Y1 - Y0):.1f}"
        for i, v in enumerate(curve))


def build_html() -> str:
    d = json.load(open(BENCH))
    bo = d["results"]["bayesian_optimization"]
    rs = d["results"]["random_search"]
    ceiling = d["surrogate_ceiling"]
    y_ceiling = Y1 - (ceiling - LO) / (HI - LO) * (Y1 - Y0)

    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{width:1280px;height:640px;background:#18222B;overflow:hidden;
       font-family:"IBM Plex Sans",system-ui,sans-serif;position:relative}}
  .wrap{{padding:74px 0 0 76px;width:660px}}
  .chip{{display:inline-block;background:#C2410C;color:#fff;font-size:15px;font-weight:600;
        letter-spacing:.14em;padding:8px 18px;border-radius:999px;margin-bottom:34px}}
  h1{{font-size:62px;font-weight:700;color:#fff;letter-spacing:-.02em;line-height:1.05}}
  .sub{{font-size:23px;color:#AEBCC8;line-height:1.5;margin-top:24px;max-width:580px}}
  .stats{{display:flex;gap:46px;margin-top:52px}}
  .s .v{{font-size:34px;font-weight:700;color:#6FA8CE;
        font-family:"IBM Plex Mono",monospace;letter-spacing:-.01em}}
  .s .l{{font-size:14px;color:#8A9AA8;margin-top:7px;line-height:1.35;max-width:150px}}
  .foot{{position:absolute;left:76px;bottom:46px;font-family:"IBM Plex Mono",monospace;
        font-size:15px;color:#64757F}}
  svg{{position:absolute;top:0;left:0}}
  .lgd{{position:absolute;right:64px;top:492px;display:flex;gap:26px;
       font-size:14px;color:#8A9AA8;align-items:center}}
  .lgd i{{display:inline-block;width:20px;height:3px;border-radius:2px;margin-right:8px;
         vertical-align:middle}}
</style></head><body>
  <div class="wrap">
    <span class="chip">AI FOR SCIENCE</span>
    <h1>AI-to-Lab<br>Orchestrator</h1>
    <p class="sub">The operating layer between an AI's next-experiment
       suggestion and the evidence that it actually ran.</p>
    <div class="stats">
      <div class="s"><div class="v">{bo['final_best']['median']:.3f}</div>
        <div class="l">BO median vs {rs['final_best']['median']:.3f} random,
        {d['seeds']} seeds</div></div>
      <div class="s"><div class="v">22</div>
        <div class="l">candidates, no simulated physics</div></div>
      <div class="s"><div class="v">65</div>
        <div class="l">tests, governance included</div></div>
    </div>
  </div>
  <div class="foot">github.com/dekunsun/ai-to-lab-orchestrator</div>
  <svg width="1280" height="640">
    <line x1="{X0}" y1="{y_ceiling:.1f}" x2="{X1}" y2="{y_ceiling:.1f}"
          stroke="#3A4650" stroke-width="2" stroke-dasharray="7 6"/>
    <polyline points="{polyline(rs['curve_median'])}" fill="none" stroke="#7D8C98"
              stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
    <polyline points="{polyline(bo['curve_median'])}" fill="none" stroke="#4E9BD1"
              stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>
    <text x="{X1}" y="{y_ceiling - 14:.1f}" text-anchor="end" fill="#5B6B78"
          font-family="IBM Plex Mono, monospace" font-size="15">ceiling {ceiling}</text>
  </svg>
  <div class="lgd">
    <span><i style="background:#4E9BD1"></i>Bayesian optimization</span>
    <span><i style="background:#7D8C98"></i>Random search</span>
  </div>
</body></html>"""


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("needs playwright: pip install playwright")

    tmp = os.path.join(os.path.dirname(OUT), "_social.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(build_html())
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chrome")
            pg = b.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=2)
            pg.goto(f"file://{tmp}", wait_until="networkidle")
            pg.wait_for_timeout(1800)          # let the webfont land before capture
            pg.screenshot(path=OUT)
            b.close()
    finally:
        os.remove(tmp)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
