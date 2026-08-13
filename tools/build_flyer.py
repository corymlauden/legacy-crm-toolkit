#!/usr/bin/env python3
"""
Build a finished flyer (.docx + .pdf) from a Word template by swapping in a
business logo and a QR code, without disturbing any of the template's fixed copy.

What it does:
  - copies the template .docx (a ZIP of XML) and unzips it
  - replaces media/image1.jpeg (the logo) and media/image2.png (the QR)
  - sets the logo's display box (wp:extent + a:ext) to match the logo's aspect
    ratio so a wide or tall logo isn't stretched into the template's square slot
  - strips the INCLUDEPICTURE field so Word can't re-fetch the template's
    original linked image at open time and silently overwrite the new logo
  - keeps every piece of the template's fixed copy untouched
  - re-zips to <slug>.docx and renders a .pdf via LibreOffice (soffice) if present

Usage:
  python3 build_flyer.py --name "Mandarin Wok" --logo logo.png --qr qr.png \
      --template template.docx --outdir ./out

The slug is the business name lowercased with non-alphanumerics removed, e.g.
"Mandarin Wok" -> mandarinwok.docx
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, zipfile
from PIL import Image

# Template's original square logo slot, expressed as the literal EMU strings that
# appear in document.xml. We replace both occurrences (wp:extent and pic a:ext),
# in the modern (mc:Choice) and the VML fallback (mc:Fallback) copies.
SQ_EXTENT = 'cx="2371781" cy="2371781"'   # wp:extent of the logo
SQ_AEXT   = 'cx="2385555" cy="2385555"'   # pic spPr a:ext of the logo

# Bounding box the logo should fit inside (EMU). 914400 EMU = 1 inch.
MAX_W = 3300000   # ~3.6"
MAX_H = 2520000   # ~2.75"

def slug(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def fit_extent(aspect):
    """Largest cx,cy preserving aspect that fits within MAX_W x MAX_H."""
    cx = min(MAX_W, int(MAX_H * aspect))
    cy = int(cx / aspect)
    return cx, cy

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Business name, e.g. 'Mandarin Wok'")
    ap.add_argument("--logo", required=True, help="Logo PNG/JPEG (any aspect, white or transparent bg)")
    ap.add_argument("--qr", required=True, help="QR PNG")
    ap.add_argument("--outdir", required=True, help="Where to write <slug>.docx/.pdf")
    ap.add_argument("--template", required=True, help="Word template .docx to swap images into")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="box_")
    ext = os.path.join(work, "ext")
    with zipfile.ZipFile(args.template) as z:
        z.extractall(ext)
    word = os.path.join(ext, "word")

    # --- logo -> image1.jpeg (flatten onto white; record aspect) ---
    logo = Image.open(args.logo)
    if logo.mode in ("RGBA", "LA", "P"):
        logo = logo.convert("RGBA")
        bg = Image.new("RGBA", logo.size, (255, 255, 255, 255))
        logo = Image.alpha_composite(bg, logo).convert("RGB")
    else:
        logo = logo.convert("RGB")
    aspect = logo.width / logo.height
    logo.save(os.path.join(word, "media", "image1.jpeg"), "JPEG", quality=95)

    # --- qr -> image2.png ---
    Image.open(args.qr).convert("RGB").save(os.path.join(word, "media", "image2.png"), "PNG")

    # --- document.xml: strip field + resize logo slot ---
    doc = os.path.join(word, "document.xml")
    xml = open(doc, encoding="utf-8").read()
    xml = re.sub(r'<w:r>\s*<w:instrText[^>]*>.*?</w:instrText>\s*</w:r>', '', xml, flags=re.S)
    xml = re.sub(r'<w:r>\s*<w:fldChar[^>]*/>\s*</w:r>', '', xml)
    cx, cy = fit_extent(aspect)
    xml = xml.replace(SQ_EXTENT, f'cx="{cx}" cy="{cy}"')
    xml = xml.replace(SQ_AEXT,   f'cx="{cx}" cy="{cy}"')
    if "INCLUDEPICTURE" in xml:
        print("WARNING: INCLUDEPICTURE still present after strip", file=sys.stderr)
    open(doc, "w", encoding="utf-8").write(xml)

    # --- re-zip ([Content_Types].xml must be first) ---
    s = slug(args.name)
    out_docx = os.path.join(args.outdir, s + ".docx")
    if os.path.exists(out_docx):
        os.remove(out_docx)
    with zipfile.ZipFile(out_docx, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(ext, "[Content_Types].xml"), "[Content_Types].xml")
        for root, _, files in os.walk(ext):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, ext)
                if arc == "[Content_Types].xml":
                    continue
                z.write(full, arc)
    print("docx:", out_docx, f"(logo aspect {aspect:.3f}, extent {cx}x{cy})")

    # --- render pdf for preview/printing ---
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                        "--outdir", args.outdir, out_docx],
                       check=False, capture_output=True)
        pdf = out_docx[:-5] + ".pdf"
        print("pdf:", pdf if os.path.exists(pdf) else "(soffice ran but no pdf?)")
    else:
        print("pdf: skipped (soffice not found)")
    shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
