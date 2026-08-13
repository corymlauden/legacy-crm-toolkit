# qr-flyer-pipeline

Print-ready marketing flyers, generated end to end: swap a business logo and a
per-record QR code into a Word template without disturbing any of its fixed copy,
then render a PDF for printing.

Built to replace a six-step manual workflow that ran several times a week — create
the record, generate its QR, find a logo, rebuild the document, check it, print it —
against a CRM that exposes **no API at all**.

```bash
python3 tools/qr_from_grid.py --grid grid.txt --out qr.png
python3 tools/text_logo.py --name "Mandarin Wok" --tagline "Authentic Chinese" \
    --city "Reading, PA" --palette red --out logo.png
python3 tools/build_flyer.py --name "Mandarin Wok" --logo logo.png --qr qr.png \
    --template template.docx --outdir ./out
```

---

## Why this is more interesting than "a script that makes flyers"

Every hard part of this came from a constraint I didn't get to choose.

**The CRM has no API.** Records are created through the browser or not at all, and
each QR code is minted server-side keyed to a contact ID. So the pipeline drives the
application programmatically rather than calling it. Along the way it has to survive
the app's undocumented behavior — most memorably, a set of single-key hotkeys that
fire whenever focus isn't inside a field and silently discard the entire unsaved
record. The fix is to never type onto the page: set every field by element reference.
That one detail is the difference between a pipeline that works and one that loses
data with no error message.

**The QR is an SVG, not an image.** It's drawn as a grid of 5px `<rect>` elements at
screen resolution, far too coarse to print. And you can't regenerate it yourself — the
URL is minted server-side and keyed to a record you don't control. The approach here
is to read the on/off module grid out of the SVG and redraw it locally at arbitrary
resolution: the same QR code, rendered sharp. That's `tools/qr_from_grid.py`.

**Getting binary data out of a sandboxed browser is genuinely hard.** No network
access in the script environment, and the browser refuses programmatic downloads. The
only channel out is a string return value capped around 700 characters. So images come
out as base64 in chunks — and chunked text transfer corrupts silently. A single wrong
character makes `zlib.decompress` fail with an error that tells you nothing about
*which* chunk broke.

The fix is a per-chunk rolling checksum computed on both sides and compared before
decoding. It is a small amount of code and it is the entire difference between this
working on the first attempt and silently producing a corrupt image. Full writeup:
**[docs/extracting-binary-data-from-a-sandboxed-browser.md](docs/extracting-binary-data-from-a-sandboxed-browser.md)**

**Word templates fight back.** A `.docx` is a ZIP of XML, so swapping images is
tractable — but two things bite. The template's logo sits in a square slot, so a wide
or tall logo gets stretched into a square unless you recompute the display extents from
the image's real aspect ratio (in EMUs; 914400 per inch, set in two places, once for
the modern markup and once for the VML fallback). And if the original image was
inserted as a linked `INCLUDEPICTURE` field, Word helpfully re-fetches the original at
open time and overwrites your replacement. That field has to be stripped from
`document.xml` or the whole swap silently reverts the moment someone opens the file.

**Half the businesses have no usable logo.** Rather than fail, or ship something
mangled out of the chunked-transfer path, `tools/text_logo.py` generates a clean
branded wordmark: a rounded panel with an accent border, the name balanced across up to
two lines, an optional tagline, and the city — every line auto-fit to the panel so
nothing overflows regardless of name length. Predictable beats clever here.

---

## Tools

| Tool | What it does |
|---|---|
| `tools/build_flyer.py` | Swaps a logo and QR into a Word template, corrects the logo's aspect ratio, strips the `INCLUDEPICTURE` field, re-zips, and renders a PDF via LibreOffice. |
| `tools/qr_from_grid.py` | Rebuilds a crisp QR PNG from a 0/1 module grid read out of an SVG-rendered QR. Configurable scale and quiet zone. |
| `tools/text_logo.py` | Generates a branded text wordmark for businesses without a logo. Four palettes, auto-fitting type. |

Run any of them with `-h` for arguments.

## Requirements

Python 3.9+ and Pillow (`pip install -r requirements.txt`). LibreOffice (`soffice`)
is optional — without it you get the `.docx` and skip PDF rendering.

## Notes

This is extracted from a working internal pipeline. The CRM-specific automation and
the original document template are omitted, since neither is mine to publish; what's
here is the reusable half. The techniques — SVG QR reconstruction, checksum-validated
chunked transfer, aspect-correct image swapping in OOXML — are the parts worth reading.

MIT licensed.
