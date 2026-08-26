# legacy-crm-toolkit

Python tools pulled out of the automation I built for the sales office I run.
Our CRM has no API. None. Records get created through the browser or not at
all, images only come out through a capped text channel, and Word documents
quietly undo your edits when you swap their images.

All of it came out of a production pipeline that took a six-step weekly job
down to one command.

```bash
python3 tools/qr_from_grid.py --grid grid.txt --out qr.png
python3 tools/text_logo.py --name "Mandarin Wok" --tagline "Authentic Chinese" \
    --city "Reading, PA" --palette red --out logo.png
python3 tools/build_flyer.py --name "Mandarin Wok" --logo logo.png --qr qr.png \
    --template template.docx --outdir ./out
```

---

## Why this is more interesting than it sounds

Every hard part of this came from a constraint I didn't get to choose.

**The CRM has no API.** Records are created through the browser or not at all,
and each QR code is minted server-side, keyed to a contact ID. So the pipeline
drives the application the way a person would. Along the way it has to survive
the app's undocumented behavior. The one I remember best is a set of
single-key hotkeys that fire whenever focus isn't inside a field and silently
throw away the entire unsaved record. The fix is to never type onto the page.
Set every field by element reference instead. That one detail is the
difference between a pipeline that works and one that loses data with no error
message.

**The QR is an SVG, not an image.** It's drawn as a grid of 5px `<rect>`
elements at screen resolution, way too coarse to print. And you can't
regenerate it yourself, because the URL is minted server-side and keyed to a
record you don't control. So the tool reads the on/off module grid out of the
SVG and redraws it locally at whatever resolution you want. Same QR code,
rendered sharp. That's `tools/qr_from_grid.py`.

**Getting binary data out of a sandboxed browser is a real pain.** No network
access in the script environment, and the browser refuses programmatic
downloads. The only channel out is a string return value capped around 700
characters. So images come out as base64 in chunks, and chunked text transfer
corrupts silently. A single wrong character makes `zlib.decompress` fail
with an error that tells you nothing about which chunk broke.

The fix is a rolling checksum on every chunk, computed on both sides and
compared before decoding. It's a small amount of code and it's the entire
difference between this working on the first try and silently producing a
corrupt image. Full writeup:
**[docs/extracting-binary-data-from-a-sandboxed-browser.md](docs/extracting-binary-data-from-a-sandboxed-browser.md)**

**Word templates fight back.** A `.docx` is a ZIP of XML, so swapping images
is doable, but two things bite. The template's logo sits in a square slot, so
a wide or tall logo gets stretched square unless you recompute the display
size from the image's real aspect ratio. That's in EMUs, 914400 per inch, set
in two places, once for the modern markup and once for the VML fallback. And
if the original image was inserted as a linked INCLUDEPICTURE field, Word
helpfully re-fetches the original when the file opens and overwrites your
replacement. That field has to be stripped out of `document.xml` or the
whole swap quietly reverts the moment someone opens the file.

**Half the businesses have no usable logo.** Rather than fail, or ship
something mangled, `tools/text_logo.py` generates a clean branded wordmark.
A rounded panel with an accent border, the name balanced across up to two
lines, an optional tagline, and the city, every line auto-fit so nothing
overflows no matter how long the name is. Predictable beats clever here.

---

## Tools

| Tool | What it does |
|---|---|
| `tools/build_flyer.py` | Swaps a logo and QR into a Word template, corrects the logo's aspect ratio, strips the INCLUDEPICTURE field, re-zips, and renders a PDF via LibreOffice. |
| `tools/qr_from_grid.py` | Rebuilds a crisp QR PNG from a 0/1 module grid read out of an SVG-rendered QR. Configurable scale and quiet zone. |
| `tools/text_logo.py` | Generates a branded text wordmark for businesses without a logo. Four palettes, auto-fitting type. |

Run any of them with `-h` for arguments.

## Requirements

Python 3.9+ and Pillow (`pip install -r requirements.txt`). LibreOffice
(`soffice`) is optional. Without it you get the `.docx` and skip the PDF.

## Notes

This is pulled from a working internal pipeline. The CRM-specific automation
and the original document template are left out, since neither is mine to
publish. What's here is the reusable half. The parts worth reading are the
SVG QR reconstruction, the checksum-validated chunked transfer, and the
aspect-correct image swapping in OOXML.

MIT licensed.
