#!/usr/bin/env python3
"""Render Figure 1 (1200x630 hero + OG social card) from committed results.json.

Panel (a): Censored token-divergence onset vs. batch size B (log2 axis, B=2..128)
           showing all 8 prompt trajectories, the Feynman trajectory, and the
           8-prompt mean ("the unplotted line").
Panel (b): Continuous prefill step-1 logit drift vs. B (mean and maximum across
           the 8 prompts).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FONT_PATH = ROOT / "fonts" / "hanken-grotesk.woff2"
RESULTS_PATH = HERE / "results.json"
SLUG = "2026-11-26-batch-size-divergence-onset"
OUT_PATH = ROOT / "images" / f"{SLUG}-hero.png"

W, H = 1200, 630
CREAM = (245, 242, 234)          # #f5f2ea
PANEL_BG = (251, 250, 246)       # #fbfaf6
INK = (26, 29, 43)               # #1a1d2b
GRID = (214, 209, 198)
MUTED_LINE = (186, 191, 207)
LIFTED_INDIGO = (112, 140, 214)
DEEP_INDIGO = (47, 65, 122)      # #2f417a
SLATE_DASH = (110, 115, 132)

BATCHES = [2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128]
XTICKS = [2, 4, 8, 16, 32, 64, 128]


def x_map(b: float, x0: int, x1: int) -> int:
    pad = 24
    lo = math.log2(2.0)
    hi = math.log2(128.0)
    frac = (math.log2(b) - lo) / (hi - lo)
    return int(round((x0 + pad) + frac * ((x1 - x0) - 2 * pad)))


def draw_rotated_ylabel(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    rx: int,
    y0: int,
    y1: int,
) -> None:
    tb = draw.textbbox((0, 0), text, font=font)
    lw = tb[2] - tb[0] + 8
    lh = tb[3] - tb[1] + 8
    txt_img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((4 - tb[0], 4 - tb[1]), text, fill=(*INK, 255), font=font)
    rot_img = txt_img.rotate(90, expand=True)
    ry = (y0 + y1) // 2 - rot_img.height // 2
    draw._image.paste(rot_img, (rx, ry), rot_img)


def draw_dashed_hline(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, color: tuple[int, int, int]) -> None:
    cx = x0
    while cx < x1:
        draw.line([(cx, y), (min(cx + 10, x1), y)], fill=color, width=2)
        cx += 18


def draw_polyline_markers(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[int, int]],
    color: tuple[int, int, int],
    width: int,
    radius: int,
    square: bool = False,
) -> None:
    if len(pts) >= 2:
        draw.line(pts, fill=color, width=width)
    for px, py in pts:
        if radius > 0:
            if square:
                draw.rectangle([px - radius, py - radius, px + radius, py + radius], fill=color, outline=INK, width=1)
            else:
                draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=color, outline=INK, width=1)


def render_image() -> Image.Image:
    res = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    font_32 = ImageFont.truetype(str(FONT_PATH), size=32)
    font_24 = ImageFont.truetype(str(FONT_PATH), size=24)

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    xlab = "batch size B"
    tb_x = draw.textbbox((0, 0), xlab, font=font_32)

    # --- Panel (a): Onset token vs batch size B ---
    ax0, ay0, ax1, ay1 = 122, 42, 578, 520
    draw.rectangle([ax0, ay0, ax1, ay1], fill=PANEL_BG)

    ymax_a = 338.0
    def ya_px(val: float) -> int:
        return int(round(ay1 - (val / ymax_a) * (ay1 - ay0)))

    for tick in [0, 64, 128, 192, 256]:
        yp = ya_px(float(tick))
        if tick > 0:
            draw.line([(ax0, yp), (ax1, yp)], fill=GRID, width=2)
        draw.line([(ax0 - 7, yp), (ax0, yp)], fill=INK, width=2)
        lbl = str(tick)
        tb = draw.textbbox((0, 0), lbl, font=font_24)
        draw.text((ax0 - 13 - (tb[2] - tb[0]), yp - (tb[3] - tb[1]) // 2 - tb[1]), lbl, fill=INK, font=font_24)

    draw_dashed_hline(draw, ax0, ax1, ya_px(257.0), SLATE_DASH)

    for pid, pdata in res["prompts"].items():
        if pid == "P1_feynman":
            continue
        pts = [(x_map(b, ax0, ax1), ya_px(float(pdata["batches"][str(b)]["censored_onset_token"]))) for b in BATCHES]
        draw.line(pts, fill=MUTED_LINE, width=2)

    feyn = res["prompts"]["P1_feynman"]
    feyn_pts = [(x_map(b, ax0, ax1), ya_px(float(feyn["batches"][str(b)]["censored_onset_token"]))) for b in BATCHES]
    draw_polyline_markers(draw, feyn_pts, LIFTED_INDIGO, width=3, radius=5, square=False)

    mean_pts = [
        (x_map(b, ax0, ax1), ya_px(float(res["batch_size_curve"][str(b)]["mean_censored_onset_tokens"])))
        for b in BATCHES
    ]
    draw_polyline_markers(draw, mean_pts, DEEP_INDIGO, width=4, radius=6, square=True)

    for bt in XTICKS:
        xp = x_map(bt, ax0, ax1)
        draw.line([(xp, ay1), (xp, ay1 + 7)], fill=INK, width=2)
        lbl = str(bt)
        tb = draw.textbbox((0, 0), lbl, font=font_24)
        draw.text((xp - (tb[2] - tb[0]) // 2, ay1 + 12 - tb[1]), lbl, fill=INK, font=font_24)

    draw.text(((ax0 + ax1) // 2 - (tb_x[2] - tb_x[0]) // 2, ay1 + 52 - tb_x[1]), xlab, fill=INK, font=font_32)
    draw_rotated_ylabel(draw, "onset token", font_32, ax0 - 94, ay0, ay1)

    draw.line([(ax0, ay0), (ax0, ay1)], fill=INK, width=3)
    draw.line([(ax0, ay1), (ax1, ay1)], fill=INK, width=3)
    draw.text((ax0 + 14, ay0 + 8), "(a)", fill=INK, font=font_32)

    lx0, ly0 = ax1 - 242, ay0 + 8
    draw.rectangle([lx0, ly0, ax1 - 10, ly0 + 74], fill=PANEL_BG, outline=GRID, width=2)
    draw.line([(lx0 + 12, ly0 + 21), (lx0 + 42, ly0 + 21)], fill=DEEP_INDIGO, width=4)
    draw.rectangle([lx0 + 22, ly0 + 16, lx0 + 32, ly0 + 26], fill=DEEP_INDIGO, outline=INK, width=1)
    tb1 = draw.textbbox((0, 0), "8-prompt mean", font=font_24)
    draw.text((lx0 + 52, ly0 + 21 - (tb1[3] - tb1[1]) // 2 - tb1[1]), "8-prompt mean", fill=INK, font=font_24)
    draw.line([(lx0 + 12, ly0 + 53), (lx0 + 42, ly0 + 53)], fill=LIFTED_INDIGO, width=3)
    draw.ellipse([lx0 + 22, ly0 + 48, lx0 + 32, ly0 + 58], fill=LIFTED_INDIGO, outline=INK, width=1)
    tb2 = draw.textbbox((0, 0), "Feynman (P1)", font=font_24)
    draw.text((lx0 + 52, ly0 + 53 - (tb2[3] - tb2[1]) // 2 - tb2[1]), "Feynman (P1)", fill=INK, font=font_24)

    # --- Panel (b): Step-1 logit drift vs batch size B ---
    bx0, by0, bx1, by1 = 718, 42, 1174, 520
    draw.rectangle([bx0, by0, bx1, by1], fill=PANEL_BG)

    ymax_b = 0.67
    def yb_px(val: float) -> int:
        return int(round(by1 - (val / ymax_b) * (by1 - by0)))

    for tick in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
        yp = yb_px(tick)
        if tick > 0:
            draw.line([(bx0, yp), (bx1, yp)], fill=GRID, width=2)
        draw.line([(bx0 - 7, yp), (bx0, yp)], fill=INK, width=2)
        lbl = f"{tick:.1f}"
        tb = draw.textbbox((0, 0), lbl, font=font_24)
        draw.text((bx0 - 13 - (tb[2] - tb[0]), yp - (tb[3] - tb[1]) // 2 - tb[1]), lbl, fill=INK, font=font_24)

    max_l_pts = [
        (x_map(b, bx0, bx1), yb_px(float(res["batch_size_curve"][str(b)]["max_step1_logit_max_abs_diff"])))
        for b in BATCHES
    ]
    mean_l_pts = [
        (x_map(b, bx0, bx1), yb_px(float(res["batch_size_curve"][str(b)]["mean_step1_logit_max_abs_diff"])))
        for b in BATCHES
    ]
    draw_polyline_markers(draw, max_l_pts, LIFTED_INDIGO, width=3, radius=5, square=False)
    draw_polyline_markers(draw, mean_l_pts, DEEP_INDIGO, width=4, radius=6, square=True)

    for bt in XTICKS:
        xp = x_map(bt, bx0, bx1)
        draw.line([(xp, by1), (xp, by1 + 7)], fill=INK, width=2)
        lbl = str(bt)
        tb = draw.textbbox((0, 0), lbl, font=font_24)
        draw.text((xp - (tb[2] - tb[0]) // 2, by1 + 12 - tb[1]), lbl, fill=INK, font=font_24)

    draw.text(((bx0 + bx1) // 2 - (tb_x[2] - tb_x[0]) // 2, by1 + 52 - tb_x[1]), xlab, fill=INK, font=font_32)
    draw_rotated_ylabel(draw, "step-1 logit drift", font_32, bx0 - 88, by0, by1)

    draw.line([(bx0, by0), (bx0, by1)], fill=INK, width=3)
    draw.line([(bx0, by1), (bx1, by1)], fill=INK, width=3)
    draw.text((bx0 + 14, by0 + 8), "(b)", fill=INK, font=font_32)

    lx0b, ly0b = bx1 - 242, by0 + 8
    draw.rectangle([lx0b, ly0b, bx1 - 10, ly0b + 74], fill=PANEL_BG, outline=GRID, width=2)
    draw.line([(lx0b + 12, ly0b + 21), (lx0b + 42, ly0b + 21)], fill=LIFTED_INDIGO, width=3)
    draw.ellipse([lx0b + 22, ly0b + 16, lx0b + 32, ly0b + 26], fill=LIFTED_INDIGO, outline=INK, width=1)
    tb_mx = draw.textbbox((0, 0), "8-prompt max", font=font_24)
    draw.text((lx0b + 52, ly0b + 21 - (tb_mx[3] - tb_mx[1]) // 2 - tb_mx[1]), "8-prompt max", fill=INK, font=font_24)
    draw.line([(lx0b + 12, ly0b + 53), (lx0b + 42, ly0b + 53)], fill=DEEP_INDIGO, width=4)
    draw.rectangle([lx0b + 22, ly0b + 48, lx0b + 32, ly0b + 58], fill=DEEP_INDIGO, outline=INK, width=1)
    tb_mn = draw.textbbox((0, 0), "8-prompt mean", font=font_24)
    draw.text((lx0b + 52, ly0b + 53 - (tb_mn[3] - tb_mn[1]) // 2 - tb_mn[1]), "8-prompt mean", fill=INK, font=font_24)

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
        tmp = Path("/tmp/batch_div_hero_check.png")
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
