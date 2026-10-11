"""Extract the 52 inlined images, re-encode as optimized WebP, and emit a map
(asset-key -> file) used by build_html.py.

Rules:
  * never upscale (the source is the quality ceiling)
  * resize only where the displayed size is far below the source size
  * lossless WebP for flat logo artwork, lossy WebP for photography
  * deduplicate by content hash so duplicate assets share one file
  * report PSNR of the re-encode so quality loss is measurable, not assumed
"""
import base64, hashlib, io, json, math, os
from PIL import Image, ImageChops, ImageStat

SRC = "elhalfawy-v20.html"
OUT = "dist/img"
os.makedirs(OUT, exist_ok=True)

# asset name -> (max_w, max_h);  None = keep native size
POLICY = {
    "logo-mark.png": (168, 192),      # navbar logo: h-11/h-14 -> ~49px wide, 3x
    "logo-white.png": (450, 160),     # footer logo: h-20 -> 225px wide, 2x
    "logo.png": (500, 178),           # present in the asset table but unused in markup
    "clients/aiu.png": (480, 183),    # client card logo: 2x of ~240px
    "clients/aiu-color.png": (480, 183),
    "sus1.jpg": (480, 640),           # one third of the sustainability triptych
    "bp-light.jpg": None,             # CSS background-size:cover on full-width sections
}
PHOTO_Q = {"hero.jpg": 80}            # the full-bleed hero gets a slightly safer setting
DEFAULT_Q = 78                        # WebP m6 q78: visually transparent for this material
LOSSLESS_PNG = True
LOSSLESS_MAX = 81920                  # keep flat logo artwork lossless up to this size


def psnr(a, b):
    """Peak signal-to-noise ratio between two same-size images, in dB.

    Alpha is flattened onto a mid-grey backdrop first, because comparing RGBA as
    RGB would score fully transparent pixels as error and report nonsense."""
    def prep(im):
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, (127, 127, 127))
            flat.paste(im, mask=im.split()[-1])
            return flat
        return im.convert("RGB")
    a, b = prep(a), prep(b)
    if a.size != b.size:
        return None
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    mse = sum(s ** 2 for s in stat.rms) / len(stat.rms)
    return float("inf") if mse == 0 else 10 * math.log10((255.0 ** 2) / mse)


def target_size(im, name):
    lim = POLICY.get(name, (1280, 1280))
    w, h = im.size
    if lim is None:
        return im, False
    mw, mh = lim
    if w <= mw and h <= mh:
        return im, False
    scale = min(mw / w, mh / h)
    return im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS), True


def encode_webp(im, name):
    is_png = name.lower().endswith(".png")
    if is_png and LOSSLESS_PNG:
        buf = io.BytesIO()
        im.save(buf, "WEBP", lossless=True, quality=100, method=6)
        if buf.tell() <= LOSSLESS_MAX:               # flat artwork: lossless stays small
            return buf.getvalue(), dict(lossless=True, q=None)
    q = PHOTO_Q.get(name, DEFAULT_Q)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=q, method=6, exact=is_png)
    return buf.getvalue(), dict(lossless=False, q=q)


def build_one(raw, name, cache, log):
    """Re-encode (with content-hash dedupe). Returns (key -> url, manifest entry)."""
    content_hash = hashlib.sha1(raw).hexdigest()
    key = (content_hash, POLICY.get(name, (1280, 1280)))
    src = Image.open(io.BytesIO(raw))
    if key in cache:
        out_name = cache[key]
        out_im = Image.open(os.path.join(OUT, out_name))
        entry = dict(name=name, key=f"./img/{name}", file=f"img/{out_name}",
                     source=dict(bytes=len(raw), w=src.size[0], h=src.size[1], format=src.format),
                     output=dict(bytes=os.path.getsize(os.path.join(OUT, out_name)),
                                 w=out_im.size[0], h=out_im.size[1], format="webp"),
                     resized=False, deduped=True, psnr=None, lossless=True, q=None)
        log(entry)
        return out_name, entry

    im2, resized = target_size(src, name)
    data, enc = encode_webp(im2, name)
    base = name.split("/")[-1].rsplit(".", 1)[0]
    out_name = f"{base}.{content_hash[:8]}.webp"
    with open(os.path.join(OUT, out_name), "wb") as f:
        f.write(data)
    cache[key] = out_name
    out_im = Image.open(io.BytesIO(data))
    entry = dict(name=name, key=f"./img/{name}", file=f"img/{out_name}",
                 source=dict(bytes=len(raw), w=src.size[0], h=src.size[1], format=src.format),
                 output=dict(bytes=len(data), w=out_im.size[0], h=out_im.size[1], format="webp"),
                 resized=resized, deduped=False, psnr=psnr(im2, out_im), **enc)
    log(entry)
    return out_name, entry


def main():
    audit = json.load(open("_audit/images.json", encoding="utf-8"))
    namemap = json.load(open("_audit/name_map.json", encoding="utf-8"))
    by_index = {r["i"]: r for r in audit}

    cache, js_map, entries = {}, {}, []

    def log(e):
        out = e["output"]
        print(f"{e['name']:>26} {e['source']['bytes']/1024:>7.1f}KB {e['source']['w']}x{e['source']['h']:<5} -> "
              f"{out['bytes']/1024:>6.1f}KB {out['w']}x{out['h']:<5}"
              f"{' resized' if e['resized'] else '        '}"
              f"{' dedupe->' + e['file'] if e['deduped'] else ''}"
              f"{'  lossless' if e['lossless'] else '  q' + str(e['q'])}"
              f"{'' if e['psnr'] in (None, float('inf')) else '  PSNR %.1f dB' % e['psnr']}")

    for rec in sorted(namemap, key=lambda r: r["i"]):
        raw = open(os.path.join("_audit/raw", by_index[rec["i"]]["file"]), "rb").read()
        out_name, entry = build_one(raw, rec["name"], cache, log)
        js_map[f"./img/{rec['name']}"] = f"./img/{out_name}"
        entries.append(entry)

    # .bp-light section texture (inline CSS background), not part of the asset table
    css_rec = [r for r in audit if r["i"] == 51][0]
    raw = open(os.path.join("_audit/raw", css_rec["file"]), "rb").read()
    out_name, entry = build_one(raw, "bp-light.jpg", cache, log)
    texture = dict(entry, key="bp-light", file=f"img/{out_name}")

    src_total = sum(e["source"]["bytes"] for e in entries) + entry["source"]["bytes"]
    out_total = sum(e["output"]["bytes"] for e in entries if not e["deduped"]) + entry["output"]["bytes"]
    manifest = dict(images=entries, css_texture=texture, map=js_map,
                    totals=dict(source_bytes=src_total, output_bytes=out_total,
                                unique_files=len(set(js_map.values())) + 1, names=len(js_map)))
    # build metadata lives outside the deploy root (dist/ is uploaded as-is)
    json.dump(manifest, open("_audit/img-manifest.json", "w"), indent=1)
    print(f"\n{len(js_map)} assets + 1 css texture: {src_total/1048576:.2f} MB -> {out_total/1048576:.2f} MB "
          f"({100 - out_total * 100 / src_total:.0f}% smaller), {manifest['totals']['unique_files']} files on disk")


if __name__ == "__main__":
    main()
