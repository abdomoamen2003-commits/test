"""Generate the production identity assets that a real deployment needs and that the
single-file build never had: favicon set and a social share image.

Everything is derived from the site's own artwork (no new branding):
  favicon.ico / favicon-32.png / apple-touch-icon.png  <- img/logo-mark.png
  og-image.jpg 1200x630                                <- img/hero.jpg (centre crop)
"""
import json, os
from PIL import Image

RAW = "_audit/raw"
OUT = "dist"
os.makedirs(OUT, exist_ok=True)

NAMES = {r["name"]: r["i"] for r in json.load(open("_audit/name_map.json"))}
audit = {r["i"]: r for r in json.load(open("_audit/images.json"))}

mark = Image.open(os.path.join(RAW, audit[NAMES["logo-mark.png"]]["file"])).convert("RGBA")
print("logo-mark.png:", mark.size, mark.mode)
bbox = mark.split()[-1].getbbox()
print("alpha bbox:", bbox)
mark = mark.crop(bbox)
print("cropped to:", mark.size)

# square canvas, transparent, ~8% breathing room (same proportions as the navbar mark)
side = int(max(mark.size) * 1.16)
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(mark, ((side - mark.size[0]) // 2, (side - mark.size[1]) // 2), mark)

icon = canvas.resize((256, 256), Image.LANCZOS)
icon.resize((32, 32), Image.LANCZOS).save(os.path.join(OUT, "favicon-32.png"), optimize=True)
icon.resize((16, 16), Image.LANCZOS).save(os.path.join(OUT, "favicon-16.png"), optimize=True)
icon.save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])

# iOS composites transparency unpredictably, so use the navbar's white ground
apple = Image.new("RGB", (180, 180), (255, 255, 255))
m = mark.resize((int(180 * mark.size[0] / max(mark.size) * 0.78), int(180 * mark.size[1] / max(mark.size) * 0.78)), Image.LANCZOS)
apple.paste(m, ((180 - m.size[0]) // 2, (180 - m.size[1]) // 2), m)
apple.save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)

hero = Image.open(os.path.join(RAW, audit[NAMES["hero.jpg"]]["file"])).convert("RGB")
w, h = hero.size
target = (1200, 630)
scale = max(target[0] / w, target[1] / h)
hero2 = hero.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
left = (hero2.size[0] - target[0]) // 2
top = (hero2.size[1] - target[1]) // 2
hero2.crop((left, top, left + target[0], top + target[1])).save(
    os.path.join(OUT, "og-image.jpg"), quality=82, optimize=True, progressive=True)

for f in ["favicon.ico", "favicon-32.png", "favicon-16.png", "apple-touch-icon.png", "og-image.jpg"]:
    print(f"{f:>22} {os.path.getsize(os.path.join(OUT, f)):>7} bytes")
