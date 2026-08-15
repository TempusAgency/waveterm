#!/usr/bin/env python3
# Copyright 2026, Tempus Agency
# SPDX-License-Identifier: Apache-2.0

"""Regenerates the fork's app icons from upstream's green ones.

The icons are binary, so a rebase onto a new upstream tag replaces them wholesale and the
recolor has to be redone rather than merged. Sources are therefore read out of git at the
base tag, never from the working tree: running this twice cannot shift the hue twice, and
it produces the same bytes after a rebase as it did before one.

The glyph is not repainted flat. Every pixel keeps its own value and alpha, so the shading,
the gradient across the two strokes and the antialiased edges survive; only the hue is
moved onto the Tempus terracotta and the saturation/value are scaled so the brightest point
of the glyph lands on #d97757. The black plate has zero saturation and is skipped.

    python3 build/tempus-icon-recolor.py                        # rewrite build/ in place
    python3 build/tempus-icon-recolor.py --preview-dir /tmp/x   # also dump 512px before/after
"""

import argparse
import colorsys
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import IcoImagePlugin, Image

DEFAULT_REF = "v0.14.5"

TEMPUS_ACCENT = (0xD9, 0x77, 0x57)

# Upstream's brightest glyph pixel, the anchor the accent is matched against.
UPSTREAM_PEAK = (0x50, 0xC0, 0x40)

# The glyph's hue spread is kept but compressed toward the accent, so the icon stays warm
# instead of fanning back out into other color families.
HUE_KEEP = 0.25

# Below this saturation a pixel is plate, shadow, or antialiasing against the plate, not glyph.
SATURATION_FLOOR = 0.15

ICNS_MEMBERS = [
    "icon_16x16.png",
    "icon_16x16@2x.png",
    "icon_32x32.png",
    "icon_32x32@2x.png",
    "icon_128x128.png",
    "icon_128x128@2x.png",
    "icon_256x256.png",
    "icon_256x256@2x.png",
    "icon_512x512.png",
    "icon_512x512@2x.png",
]

PREVIEW_MEMBER = "icon_512x512.png"


def _hsv(rgb):
    return colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


ACCENT_H, ACCENT_S, ACCENT_V = _hsv(TEMPUS_ACCENT)
PEAK_H, PEAK_S, PEAK_V = _hsv(UPSTREAM_PEAK)
SAT_SCALE = ACCENT_S / PEAK_S
VAL_SCALE = ACCENT_V / PEAK_V


def recolor(img):
    img = img.convert("RGBA")
    out = img.copy()
    src = img.load()
    dst = out.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if ss < SATURATION_FLOOR:
                continue
            # hue is circular, so measure the offset from upstream's peak the short way round
            delta = ((hh - PEAK_H + 0.5) % 1.0) - 0.5
            nh = (ACCENT_H + delta * HUE_KEEP) % 1.0
            ns = min(1.0, ss * SAT_SCALE)
            nv = min(1.0, vv * VAL_SCALE)
            nr, ng, nb = colorsys.hsv_to_rgb(nh, ns, nv)
            dst[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def git_show(repo, ref, rel, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fp:
        subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{rel}"], stdout=fp, check=True)


def git_ls_icons(repo, ref):
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "--name-only", f"{ref}:build/icons"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [n for n in proc.stdout.split() if n.endswith(".png")]


def build_icns(repo, ref, work, out):
    src = work / "src.icns"
    git_show(repo, ref, "build/icon.icns", src)
    iconset = work / "src.iconset"
    subprocess.run(["iconutil", "-c", "iconset", str(src), "-o", str(iconset)], check=True)

    recolored = work / "tempus.iconset"
    recolored.mkdir()
    preview = None
    for name in ICNS_MEMBERS:
        member = iconset / name
        if not member.exists():
            continue
        img = recolor(Image.open(member))
        img.save(recolored / name)
        if name == PREVIEW_MEMBER:
            preview = img
    subprocess.run(["iconutil", "-c", "icns", str(recolored), "-o", str(out)], check=True)
    return preview


def build_ico(repo, ref, work, out):
    src = work / "src.ico"
    git_show(repo, ref, "build/icon.ico", src)
    with src.open("rb") as fp:
        ico = IcoImagePlugin.IcoFile(fp)
        frames = [recolor(ico.frame(i)) for i in range(ico.nb_items)]
    frames.sort(key=lambda im: im.size[0], reverse=True)
    # append_images hands ICO one artwork per size, so the hand-tuned small frames survive
    # instead of being resampled down from the largest one
    frames[0].save(out, format="ICO", sizes=[im.size for im in frames], append_images=frames[1:])


def build_pngs(repo, ref, work, out_dir):
    for name in git_ls_icons(repo, ref):
        src = work / "icons" / name
        git_show(repo, ref, f"build/icons/{name}", src)
        recolor(Image.open(src)).save(out_dir / name)


def main():
    repo = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default=DEFAULT_REF, help="git ref holding upstream's icons")
    ap.add_argument("--preview-dir", help="write 512px before/after PNGs here")
    args = ap.parse_args()

    build = repo / "build"
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        after = build_icns(repo, args.ref, work, build / "icon.icns")
        build_ico(repo, args.ref, work, build / "icon.ico")
        build_pngs(repo, args.ref, work, build / "icons")

        if args.preview_dir:
            pd = pathlib.Path(args.preview_dir)
            pd.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / "src.iconset" / PREVIEW_MEMBER, pd / "icon-512-before.png")
            after.save(pd / "icon-512-after.png")
            print(f"preview: {pd}")

    print(f"recolored build/icon.icns, build/icon.ico and build/icons/*.png from {args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
