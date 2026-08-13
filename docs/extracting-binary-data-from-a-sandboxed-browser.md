# Getting images and binary data out of a sandboxed browser

*Notes from automating a document pipeline against a web app that had no API.*

The constraint: the script environment had **no network access**, and the browser **refused programmatic downloads** (no user gesture). So you can't `curl` an image and you can't trigger a download from JS.

The reliable path is to read pixels in the browser via a `<canvas>` and carry the bytes back as text through the JS evaluation channel's return value. That return was **truncated at roughly 700 characters per call**, which is why everything below is chunked and checksum-validated.

The technique generalizes to any situation where your only channel out of a browser is a length-capped string.

This file covers two jobs: extracting the **QR grid** (tiny — easy), and pulling a **real logo** (bigger — needs care).

---

## Case 1 — extracting a QR module grid

The QR was an SVG of 5px `<rect>` modules, 33×33. Read it as a 0/1 grid. It fits in two calls (rows 0–16, then 17–end).

First call — build the grid, stash it, return the first half:
```js
(() => {
  const qr = [...document.querySelectorAll('svg')]
    .find(s => s.getAttribute('width')==='230' && s.getAttribute('height')==='230');
  const rects=[...qr.querySelectorAll('rect')];
  const xs=rects.map(r=>+r.getAttribute('x')), ys=rects.map(r=>+r.getAttribute('y'));
  const minX=Math.min(...xs),minY=Math.min(...ys),step=5;
  const cols=Math.round((Math.max(...xs)-minX)/step)+1, rows=Math.round((Math.max(...ys)-minY)/step)+1;
  const g=Array.from({length:rows},()=>Array(cols).fill('0'));
  for(const r of rects){const cx=Math.round((+r.getAttribute('x')-minX)/step),cy=Math.round((+r.getAttribute('y')-minY)/step);g[cy][cx]='1';}
  window.__grid=g.map(r=>r.join(''));
  return JSON.stringify({rows, cols, firstHalf: window.__grid.slice(0,17).join('\n')});
})()
```
Second call — the rest:
```js
window.__grid.slice(17).join('\n')
```
Concatenate the two halves into a 33-line file and run `qr_from_grid.py`.

---

## Case 2 — pulling a real image

Open the logo image in its own browser tab (navigate the tab directly to the image URL so the page is **same-origin** with the image — otherwise the canvas is tainted and `toDataURL` throws). Find the logo URL first by reading the business site's `<img>` elements; many small sites are client-rendered, so inspect in the browser rather than via web_fetch.

### Case A — simple line-art logo (mostly black on white)
Threshold to 1-bit and deflate. It compresses to a few KB. Chunk it out at ≤700 chars/call and rebuild with Pillow in the sandbox. (For very simple art, run-length encoding is even smaller.)

### Case B — detailed / color logo
This is the one that needs discipline. Steps in the browser tab (same-origin with the image):

1. Draw the image to a canvas; for color logos that are essentially 2 inks on white, **quantize to a small palette** (e.g. white + the two brand colors + black) — large flat regions then deflate well. Downscale to ~200–340px on the long edge to keep the payload small (≈8–20 KB base64). 200px gives ~13 chunks; bigger means more chunks and more chances to mis-transcribe.
2. Pack the palette **indices** (1 byte/pixel), `deflate` them with `CompressionStream`, base64 the result, and stash on `window.__logo`.
3. **Get a per-chunk checksum from the browser** so you can verify the transcription:
```js
// after window.__logo is set:
(() => { let o=[]; const N=window.__logo.length;
  for(let k=0;k*700<N;k++){ const s=window.__logo.substr(k*700,700);
    let sum=0; for(let i=0;i<s.length;i++) sum=(sum*31+s.charCodeAt(i))>>>0;
    o.push(k+':'+s.length+':'+sum); }
  return JSON.stringify({len:N, chunks:o}); })()
```
4. Pull each chunk with a delimiter, **≤4 parallel calls at a time** (more overloaded the browser connection and calls silently failed):
```js
'C7<'+window.__logo.substr(7*700,700)+'>'
```
5. In the sandbox, recompute the same rolling checksum (`sum = (sum*31 + ord(ch)) & 0xffffffff`) for each pasted chunk and compare to the browser's. **Fix any mismatch before decoding** — `zlib.decompress` fails on a single wrong character, and the failure doesn't tell you which chunk. Then base64-decode → `zlib.decompress` → map indices back through the palette → save PNG.

### Why bother
The checksum step is the difference between this working first try and silently corrupting. Don't skip it. And if the image is complex or the transfer is painful, there is always the fallback of generating a clean substitute instead — `tools/text_logo.py` in this repo does that. A generated wordmark beats a mangled logo.

---

## Result
After either of these you have a `logo.png` and a `qr.png` locally. Hand both to `tools/build_flyer.py`.
