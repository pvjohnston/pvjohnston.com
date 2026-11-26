#!/usr/bin/env python3
"""Render Figure 1 (1200x630 hero + OG social card) from committed results.json files.

Compares (a) the two-level composite populations from `research/smx-conformer-thermochemistry`
(`source DFT + GFN2-xTB/ALPB`) against (b) the single-surface `B3LYPG-D3(BJ)/def2-TZVP +
IEF-PCM(water)` populations from this experiment, using committed Hanken Grotesk at 32px.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FONT_PATH = ROOT / "fonts" / "hanken-grotesk.woff2"
PRIOR_RESULTS = ROOT / "research" / "smx-conformer-thermochemistry" / "results.json"
SINGLE_RESULTS = HERE / "results.json"
SLUG = "2026-11-26-smx-single-surface-thermochemistry"
OUT_PATH = ROOT / "images" / f"{SLUG}-hero.png"

W, H = 1200, 630
CREAM = (245, 242, 234)       # #f5f2ea
PANEL_BG = (251, 250, 246)    # #fbfaf6
INK = (26, 29, 43)            # #1a1d2b
GRID = (214, 209, 198)
ELEC_FILL = (196, 198, 206)
ELEC_EDGE = (92, 97, 115)
RRHO_FILL = (143, 165, 227)   # #8fa5e3 lifted indigo
RRHO_EDGE = (47, 65, 122)     # #2f417a deep indigo
MRRHO_FILL = (47, 65, 122)    # #2f417a deep indigo
MRRHO_EDGE = (26, 29, 43)     # #1a1d2b ink

CONFORMERS = ("A", "B", "C", "D")


def draw_panel(
    draw: ImageDraw.ImageDraw,
    font_32: ImageFont.FreeTypeFont,
    font_26: ImageFont.FreeTypeFont,
    box: tuple[int, int, int, int],
    panel_tag: str,
    series: list[tuple[str, dict[str, float], tuple[int, int, int], tuple[int, int, int]]],
    show_ylabel: bool,
    show_legend: bool,
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], fill=PANEL_BG)

    ymax = 55.0
    yticks = [0, 10, 20, 30, 40, 50]

    def y_px(val: float) -> int:
        return int(round(y1 - (val / ymax) * (y1 - y0)))

    # Horizontal gridlines and y ticks
    for tick in yticks:
        yp = y_px(float(tick))
        if tick > 0:
            draw.line([(x0, yp), (x1, yp)], fill=GRID, width=2)
        draw.line([(x0 - 7, yp), (x0, yp)], fill=INK, width=2)
        label = str(tick)
        bbox = draw.textbbox((0, 0), label, font=font_26)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x0 - 14 - tw, yp - th // 2 - bbox[1]), label, fill=INK, font=font_26)

    # 25% uniform reference dashed line
    y25 = y_px(25.0)
    dash_x = x0
    while dash_x < x1:
        draw.line([(dash_x, y25), (min(dash_x + 10, x1), y25)], fill=ELEC_EDGE, width=2)
        dash_x += 18

    # Grouped bars
    group_span = (x1 - x0) / len(CONFORMERS)
    bar_w = 24
    gap = 5
    total_group_w = 3 * bar_w + 2 * gap

    for idx, conf in enumerate(CONFORMERS):
        cx = x0 + (idx + 0.5) * group_span
        start_x = cx - total_group_w / 2.0
        for s_idx, (_, pops, fill_c, edge_c) in enumerate(series):
            val = 100.0 * float(pops[conf])
            bx0 = int(round(start_x + s_idx * (bar_w + gap)))
            bx1 = bx0 + bar_w
            by0 = y_px(val)
            draw.rectangle([bx0, by0, bx1, y1], fill=fill_c, outline=edge_c, width=2)

        # X tick & label
        cx_i = int(round(cx))
        draw.line([(cx_i, y1), (cx_i, y1 + 7)], fill=INK, width=2)
        bbox = draw.textbbox((0, 0), conf, font=font_32)
        tw = bbox[2] - bbox[0]
        draw.text((cx_i - tw // 2, y1 + 14 - bbox[1]), conf, fill=INK, font=font_32)

    # Left and bottom axes
    draw.line([(x0, y0), (x0, y1)], fill=INK, width=3)
    draw.line([(x0, y1), (x1, y1)], fill=INK, width=3)

    # Panel letter callout
    draw.text((x0 + 16, y0 + 12), panel_tag, fill=INK, font=font_32)

    # Rotated y-axis label
    if show_ylabel:
        ylabel = "population (%)"
        tb = draw.textbbox((0, 0), ylabel, font=font_32)
        lw = tb[2] - tb[0] + 8
        lh = tb[3] - tb[1] + 8
        txt_img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((4 - tb[0], 4 - tb[1]), ylabel, fill=(*INK, 255), font=font_32)
        rot_img = txt_img.rotate(90, expand=True)
        ry = (y0 + y1) // 2 - rot_img.height // 2
        rx = x0 - 92
        draw._image.paste(rot_img, (rx, ry), rot_img)

    # Legend in panel (b)
    if show_legend:
        lx0 = x1 - 224
        ly0 = y0 + 14
        row_h = 34
        box_h = 18 + len(series) * row_h
        draw.rectangle([lx0, ly0, x1 - 12, ly0 + box_h], fill=PANEL_BG, outline=GRID, width=2)
        for s_idx, (label, _, fill_c, edge_c) in enumerate(series):
            ry = ly0 + 12 + s_idx * row_h
            draw.rectangle([lx0 + 14, ry + 4, lx0 + 38, ry + 24], fill=fill_c, outline=edge_c, width=2)
            tb = draw.textbbox((0, 0), label, font=font_26)
            draw.text((lx0 + 50, ry + 14 - (tb[3] - tb[1]) // 2 - tb[1]), label, fill=INK, font=font_26)


def render_image() -> Image.Image:
    prior = json.loads(PRIOR_RESULTS.read_text(encoding="utf-8"))
    single = json.loads(SINGLE_RESULTS.read_text(encoding="utf-8"))

    font_32 = ImageFont.truetype(str(FONT_PATH), size=32)
    font_26 = ImageFont.truetype(str(FONT_PATH), size=26)

    for glyph in "()abABCD0123456789.%populationelctrhms ":
        font_32.getmask(glyph)

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    prior_series = [
        ("electronic", prior["source_preflight"]["electronic_populations"], ELEC_FILL, ELEC_EDGE),
        ("rrho", prior["analysis"]["rrho"]["composite_populations"], RRHO_FILL, RRHO_EDGE),
        ("mrrho50", prior["analysis"]["mrrho50"]["composite_populations"], MRRHO_FILL, MRRHO_EDGE),
    ]
    single_series = [
        ("electronic", single["single_surface_electronic_baseline"]["populations"], ELEC_FILL, ELEC_EDGE),
        ("rrho", single["primary_single_surface_analysis"]["rrho"]["populations"], RRHO_FILL, RRHO_EDGE),
        ("mrrho50", single["primary_single_surface_analysis"]["mrrho50"]["populations"], MRRHO_FILL, MRRHO_EDGE),
    ]

    draw_panel(
        draw,
        font_32,
        font_26,
        box=(126, 48, 616, 542),
        panel_tag="(a)",
        series=prior_series,
        show_ylabel=True,
        show_legend=False,
    )
    draw_panel(
        draw,
        font_32,
        font_26,
        box=(686, 48, 1176, 542),
        panel_tag="(b)",
        series=single_series,
        show_ylabel=False,
        show_legend=True,
    )
    return img


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    img = render_image()
    if args.check:
        if not OUT_PATH.is_file():
            print(f"{OUT_PATH} is missing", file=sys.stderr)
            return 1
        tmp = Path("/tmp/smx_single_surface_hero_check.png")
        img.save(tmp, format="PNG")
        if hashlib.sha256(tmp.read_bytes()).hexdigest() != hashlib.sha256(OUT_PATH.read_bytes()).hexdigest():
            tmp.unlink(missing_ok=True)
            print(f"{OUT_PATH} does not match canonical regeneration", file=sys.stderr)
            return 1
        tmp.unlink(missing_ok=True)
        print(f"{OUT_PATH.name} matches canonical regeneration (1200x630)")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH, format="PNG")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({img.size[0]}x{img.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
