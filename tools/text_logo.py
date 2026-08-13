#!/usr/bin/env python3
"""
Generate a clean branded text wordmark for a business that has no usable logo.

Produces an emblem on a white background: a colored rounded panel with a thin
accent border, the business name (split across up to two lines), an optional
tagline inside the panel, and the city below it. Every line is auto-fit to the
panel width so nothing overflows regardless of name length.

This is the fast, reliable fallback for businesses without a usable logo --
much quicker and more predictable than pulling and color-quantizing a real logo
out of a web page.

Pick a palette that fits the business vibe (default is a classic red/gold that
reads well for restaurants); pass --palette to change it.

Usage:
  python3 text_logo.py --name "Mandarin Wok" --tagline "Authentic Chinese Cuisine" \
      --city "Reading, PA" --out logo.png [--palette red]

Palettes: red (red/gold), green (forest/cream), navy (navy/gold), black (black/gold).
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

PALETTES = {
    "red":   dict(panel=(176, 16, 28),  border=(212,175,55), main=(255,247,224), accent=(212,175,55), city=(140,12,22)),
    "green": dict(panel=(20, 92, 58),   border=(226,205,150), main=(255,250,235), accent=(226,205,150), city=(18,70,46)),
    "navy":  dict(panel=(20, 38, 74),   border=(212,175,55), main=(255,247,224), accent=(212,175,55), city=(20,38,74)),
    "black": dict(panel=(22, 22, 24),   border=(212,175,55), main=(245,245,245), accent=(212,175,55), city=(22,22,24)),
}

W, H = 760, 720

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--tagline", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--palette", default="red", choices=list(PALETTES))
    args = ap.parse_args()
    C = PALETTES[args.palette]

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    def fit(txt, maxw, maxsz, trr=0.06):
        sz = maxsz
        while sz > 8:
            f = ImageFont.truetype(SERIF, sz)
            tr = sz * trr
            w = sum(d.textlength(c, font=f) + tr for c in txt) - tr
            if w <= maxw:
                return f, tr, w
            sz -= 2
        f = ImageFont.truetype(SERIF, 8)
        return f, 0, d.textlength(txt, font=f)

    def ctext(y, txt, maxw, maxsz, fill, trr=0.06):
        f, tr, w = fit(txt, maxw, maxsz, trr)
        x = (W - w) / 2
        for c in txt:
            d.text((x, y), c, font=f, fill=fill)
            x += d.textlength(c, font=f) + tr

    # panel
    d.rounded_rectangle([34, 70, 726, 560], radius=46, fill=C["panel"])
    d.rounded_rectangle([54, 90, 706, 540], radius=34, outline=C["border"], width=5)
    INNER = 590

    # split name into <=2 lines (split near the middle on a space if multi-word)
    words = args.name.upper().split()
    if len(words) == 1:
        lines = words
    else:
        # balance: put roughly half the characters on each line
        best, bestdiff = 1, 1e9
        for i in range(1, len(words)):
            a = " ".join(words[:i]); b = " ".join(words[i:])
            diff = abs(len(a) - len(b))
            if diff < bestdiff:
                bestdiff, best = diff, i
        lines = [" ".join(words[:best]), " ".join(words[best:])]

    # top ornament
    d.line([(160, 150), (600, 150)], fill=C["border"], width=3)
    d.ellipse([372, 141, 388, 157], fill=C["border"])

    if len(lines) == 1:
        ctext(250, lines[0], INNER, 150, C["accent"], 0.12)
    else:
        ctext(176, lines[0], INNER, 96, C["main"], 0.08)
        ctext(296, lines[1], INNER, 150, C["accent"], 0.12)

    d.line([(160, 500), (600, 500)], fill=C["border"], width=3)
    if args.tagline:
        sep = "  ".join(args.tagline.upper().split())
        ctext(456, sep, INNER, 30, C["main"], 0.05)

    if args.city:
        ctext(610, args.city, 420, 46, C["city"], 0.04)

    img.save(args.out)
    print(f"logo {img.size} -> {args.out}  lines={lines}")

if __name__ == "__main__":
    main()
