#!/usr/bin/env python3
"""
Rebuild a crisp QR PNG from a module grid extracted out of an SVG-rendered QR code.

Why this exists: some web applications render QR codes as an SVG of <rect>
modules rather than a raster image, at a screen resolution too low to print. If
you also can't re-encode the payload yourself -- the URL is minted server-side
and keyed to a record ID -- you can't just regenerate it with a QR library.

The reliable path is to read the on/off module grid straight out of the SVG in
the browser and redraw it here at arbitrary resolution. The result is the exact
same QR code, rendered sharply enough for print.

Grid input: a text file (or stdin) of N lines, each N characters of '0'/'1'
('1' = black module). A typical Version-4 QR is 33x33.

In the browser console, extract the grid like this on the page showing the QR:

    const qr = [...document.querySelectorAll('svg')]
      .find(s => s.getAttribute('width')==='230' && s.getAttribute('height')==='230');
    const rects=[...qr.querySelectorAll('rect')];
    const xs=rects.map(r=>+r.getAttribute('x')), ys=rects.map(r=>+r.getAttribute('y'));
    const minX=Math.min(...xs),minY=Math.min(...ys),step=5;
    const cols=Math.round((Math.max(...xs)-minX)/step)+1, rows=Math.round((Math.max(...ys)-minY)/step)+1;
    const g=Array.from({length:rows},()=>Array(cols).fill('0'));
    for(const r of rects){const cx=Math.round((+r.getAttribute('x')-minX)/step),cy=Math.round((+r.getAttribute('y')-minY)/step);g[cy][cx]='1';}
    g.map(r=>r.join('')).join('\n');   // returns the grid text

Output truncates around ~700 chars per browser call, so pull it in two halves
(rows 0..16 then 17..end) and concatenate.

Usage:
  python3 qr_from_grid.py --grid grid.txt --out qr.png [--scale 24] [--border 4]
"""
import argparse, sys
from PIL import Image

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", help="text file of 0/1 rows; omit to read stdin")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=24, help="pixels per module")
    ap.add_argument("--border", type=int, default=4, help="quiet-zone modules")
    args = ap.parse_args()

    text = open(args.grid).read() if args.grid else sys.stdin.read()
    rows = [r.strip() for r in text.strip().splitlines() if r.strip()]
    n = len(rows)
    if not all(len(r) == n for r in rows):
        sys.exit(f"Grid must be square; got rows of lengths {sorted(set(len(r) for r in rows))}")

    sc, bd = args.scale, args.border
    size = (n + 2 * bd) * sc
    img = Image.new("1", (size, size), 1)  # white
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "1":
                x0, y0 = (x + bd) * sc, (y + bd) * sc
                for dy in range(sc):
                    for dx in range(sc):
                        px[x0 + dx, y0 + dy] = 0
    img.save(args.out)
    print(f"QR {img.size} ({n}x{n} modules) -> {args.out}")

if __name__ == "__main__":
    main()
