import re, os, base64, io, json, hashlib
from PIL import Image

SRC = "elhalfawy-v20.html"
OUT = "_audit/raw"
os.makedirs(OUT, exist_ok=True)

data = open(SRC, "rb").read()
pat = re.compile(rb'data:image/([a-zA-Z+]+);base64,([A-Za-z0-9+/=]+)')

rows = []
for i, m in enumerate(pat.finditer(data)):
    fmt = m.group(1).decode()
    b64 = m.group(2)
    start, end = m.start(), m.end()
    raw = base64.b64decode(b64)
    h = hashlib.sha1(raw).hexdigest()[:10]
    # context before/after inside the bundle
    pre = data[max(0, start - 150):start].decode("utf-8", "replace")
    post = data[end:end + 90].decode("utf-8", "replace")
    line = data[:start].count(b"\n") + 1
    try:
        im = Image.open(io.BytesIO(raw))
        w, hh = im.size
        mode = im.mode
    except Exception as e:
        w = hh = 0
        mode = "ERR:" + str(e)
    ext = "jpg" if fmt == "jpeg" else fmt
    fn = f"{i:02d}_{h}.{ext}"
    open(os.path.join(OUT, fn), "wb").write(raw)
    rows.append(dict(i=i, fmt=fmt, bytes=len(raw), b64len=len(b64), w=w, h=hh,
                     mode=mode, line=line, off=start, file=fn, pre=pre[-150:], post=post))

with open("_audit/images.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1, ensure_ascii=False)

print(f"{'#':>3} {'fmt':>5} {'KB':>8} {'WxH':>12} {'line':>5}  context-before")
for r in rows:
    print(f"{r['i']:>3} {r['fmt']:>5} {r['bytes']/1024:>8.1f} {r['w']}x{r['h']:<6} {r['line']:>5}  ...{r['pre'][-95:].strip()}")

print()
print("TOTAL decoded image bytes:", sum(r['bytes'] for r in rows), f"({sum(r['bytes'] for r in rows)/1048576:.2f} MB)")
print("TOTAL base64 chars       :", sum(r['b64len'] for r in rows), f"({sum(r['b64len'] for r in rows)/1048576:.2f} MB)")
print("SOURCE html bytes        :", len(data))
