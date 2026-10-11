"""Build dist/index.html from the single-file build.

Every edit is anchored to an exact byte offset found during the audit, so nothing
else in the 6 MB document (markup, CSS, app code) is touched:

  1. 52 inlined base64 images  -> external, cacheable, lazily-loaded files
  2. 22 <img> render sites     -> decoding/loading hints (hero + logos stay eager)
  3. Google Fonts <link>       -> self-hosted variable font (one 27 KB file)
  4. production head           -> favicon, apple-touch-icon, canonical, OG/Twitter,
                                  theme-color, JSON-LD, noscript fallback
  5. mx-prod <style>           -> @font-face + horizontal-overflow fix
"""
import json, re, sys

SRC = "elhalfawy-v20.html"
OUT = "dist/index.html"
SITE = "https://www.elhalfawy.com/"

html = open(SRC, "r", encoding="utf-8", errors="surrogateescape").read()
man = json.load(open("_audit/img-manifest.json", encoding="utf-8"))
audit = json.load(open("_audit/images.json", encoding="utf-8"))
namemap = {r["i"]: r["name"] for r in json.load(open("_audit/name_map.json", encoding="utf-8"))}

edits = []          # (start, end, replacement)
report = []

# ---------------------------------------------------------------- 1. images
# Anchor on the asset variable declaration (`Vz="data:image/..."`) rather than on
# byte offsets: the document contains multi-byte characters, so byte offsets and
# string offsets do not line up.
uri_re = re.compile(r'data:image/[a-zA-Z+]+;base64,[A-Za-z0-9+/=]+')
img_map = dict(man["map"])
img_map["bp-light"] = "./" + man["css_texture"]["file"]
namemap_text = json.load(open("_audit/name_map.json", encoding="utf-8"))
for rec in namemap_text:
    key = f"./img/{rec['name']}"
    anchor = f'{rec["var"]}="data:image'
    if html.count(anchor) != 1:
        sys.exit(f"anchor not unique for {rec['name']}: {anchor}")
    start = html.index(anchor) + len(rec["var"]) + 2      # keep the opening quote, skip it
    m = uri_re.match(html, start)
    if not m:
        sys.exit(f"malformed data URI for {rec['name']}")
    edits.append((m.start(), m.end(), img_map[key]))
    report.append(("image", key, img_map[key], len(m.group(0))))

# the .bp-light section texture is an inline CSS background, not an asset-module string
css_anchor = '.bp-light{background-image:url(data:image'
if html.count(css_anchor) != 1:
    sys.exit("bp-light css anchor not unique")
cm = uri_re.match(html, html.index(css_anchor) + len('.bp-light{background-image:url('))
edits.append((cm.start(), cm.end(), img_map["bp-light"]))
report.append(("image", "bp-light (css texture)", img_map["bp-light"], len(cm.group(0))))

# ------------------------------------------------------- 2. <img> attributes
LAZY = 'loading:"lazy",decoding:"async",'
EAGER = 'decoding:"async",'
HERO = 'fetchpriority:"high",decoding:"async",'
# index -> hint, taken from each site's position in the page (audit: _audit/imgsites.txt)
HINTS = {
    0: EAGER,   # navbar logo (above the fold on every page)
    1: LAZY,    # footer logo
    2: HERO,    # home hero background -- the LCP image
    3: LAZY,    # featured project slider
    4: LAZY, 5: LAZY, 6: LAZY,
    # 7/8 are the client logo tiles: the colour variant sits in a hover-revealed layer
    # that has no box until hover, so lazy loading would show an empty tile on hover.
    # All six client logos together are ~33 KB, so they load with the page.
    7: EAGER, 8: EAGER,
    9: EAGER,   # inner-page header background (above the fold)
    10: LAZY, 11: LAZY, 12: LAZY, 13: LAZY, 14: LAZY, 15: LAZY, 16: LAZY, 17: LAZY,
    18: LAZY, 19: LAZY, 20: LAZY, 21: LAZY,
}
sites = [m.start() for m in re.finditer(r'jsx\("img",\{', html)]
if len(sites) != 22:
    sys.exit(f"expected 22 img sites, found {len(sites)}")
for n, off in enumerate(sites):
    edits.append((off + len('jsx("img",{'), off + len('jsx("img",{'), HINTS[n]))
    report.append(("img-hint", str(n), HINTS[n].split(',')[0], 0))

# ------------------------------------------------- 3. form field semantics
# The contact form builds every control from one factory and already emits
# aria-invalid / aria-describedby, but never tells assistive tech which fields are
# mandatory (the label only carries a visual "*"). `required` + `aria-required` are
# purely semantic here: the form is noValidate, so the custom inline validation,
# focus management and messages all stay exactly as they are.
FACTORY = 'const bad=er[k],c={id:"mx-"+k,name:k,value:v[k],onChange:x=>set(k,x.target.value),onBlur:()=>blur(k),'
if html.count(FACTORY) != 1:
    sys.exit("form field factory anchor not unique")
fk = html.index(FACTORY)
ins = '...(o.req?{required:!0,"aria-required":"true"}:0),'
edits.append((fk + len(FACTORY), fk + len(FACTORY), ins))
report.append(("form", "required/aria-required", "3 mandatory fields", 0))

# ------------------------------------------------------------ 3. font link
font_links = """    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />"""
new_font = """    <link rel="preload" href="./fonts/plus-jakarta-sans-latin.woff2" as="font" type="font/woff2" crossorigin />"""
if font_links not in html:
    sys.exit("font links not found verbatim")
i = html.index(font_links)
edits.append((i, i + len(font_links), new_font))
report.append(("fonts", "google->self-hosted", "fonts/plus-jakarta-sans-latin.woff2", 0))

# ------------------------------------------------------------ 4. head meta
title = "<title>El Halfawy | Architecture & General Contracting</title>"
DESC = ("El Halfawy — Architecture & General Contracting. Reliable construction, finishing "
        "and project management across Egypt.")
head_add = title + """
    <meta name="theme-color" content="#0a3641" />
    <meta name="color-scheme" content="light" />
    <link rel="canonical" href="{site}" />
    <link rel="icon" href="./favicon.ico" sizes="any" />
    <link rel="icon" type="image/png" href="./favicon-32.png" sizes="32x32" />
    <link rel="icon" type="image/png" href="./favicon-16.png" sizes="16x16" />
    <link rel="apple-touch-icon" href="./apple-touch-icon.png" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="El Halfawy" />
    <meta property="og:title" content="El Halfawy | Architecture &amp; General Contracting" />
    <meta property="og:description" content="{desc}" />
    <meta property="og:url" content="{site}" />
    <meta property="og:image" content="{site}og-image.jpg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="El Halfawy construction site" />
    <meta property="og:locale" content="en_EG" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="El Halfawy | Architecture &amp; General Contracting" />
    <meta name="twitter:description" content="{desc}" />
    <meta name="twitter:image" content="{site}og-image.jpg" />
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"GeneralContractor","name":"El Halfawy","description":"{desc}","url":"{site}","telephone":"+201117773238","email":"Israa.elhalfawy@hotmail.com","address":{{"@type":"PostalAddress","addressCountry":"EG"}},"geo":{{"@type":"GeoCoordinates","latitude":29.9711933,"longitude":31.3149014}},"areaServed":"Egypt","image":"{site}og-image.jpg"}}</script>""".format(site=SITE, desc=DESC)
j = html.index(title)
edits.append((j, j + len(title), head_add))
report.append(("head", "meta/OG/JSON-LD/favicon", "inserted", 0))

# ------------------------------------------------------- 5. noscript + style
noscript = """    <div id="root"></div>
    <noscript>
      <div style="max-width:44rem;margin:12vh auto;padding:0 1.5rem;font:400 1rem/1.7 'Plus Jakarta Sans',system-ui,sans-serif;color:#0a3641">
        <h1 style="font-weight:800;font-size:1.6rem;margin:0 0 .75rem">El Halfawy — Architecture &amp; General Contracting</h1>
        <p style="margin:0 0 1rem">This site needs JavaScript to display the full experience. You can still reach us directly:</p>
        <p style="margin:0"><a style="color:#EC9510" href="tel:+201117773238">+20 111 777 3238</a><br />
        <a style="color:#EC9510" href="mailto:Israa.elhalfawy@hotmail.com">Israa.elhalfawy@hotmail.com</a></p>
      </div>
    </noscript>"""
root = '    <div id="root"></div>'
k = html.index(root)
edits.append((k, k + len(root), noscript))
report.append(("body", "noscript fallback", "inserted", 0))

PROD_CSS = """
  <style id="mx-prod">
/* ==========================================================================
   El Halfawy — Production layer  (additive, no branding changes)
   1. self-hosted variable font                2. horizontal-overflow fix
   3. resilience helpers
   ========================================================================== */
/* 1. Plus Jakarta Sans, weights 400-800, latin subset — one 27 KB file instead of
   five webfont requests from fonts.gstatic.com. Same family, same metrics. */
@font-face{font-family:'Plus Jakarta Sans';font-style:normal;font-weight:400 800;font-display:swap;
  src:url(./fonts/plus-jakarta-sans-latin.woff2) format('woff2');
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}

/* 2. Horizontal-overflow fix. The drifting ambient glows (section.bp::after and
   friends) hang 20% outside their section, and the AOS fade-left/fade-right
   entrance offsets push cards +-100px, so the page could be dragged sideways
   past the layout into empty space (a 17 px scrollbar plus 285 px of dead scroll
   on desktop, side-swipeable on touch).
   The clip is applied to the VIEWPORT ONLY - never to a section - so a glow that
   bleeds across a section boundary still paints exactly as designed. Only the
   off-screen part, which no visitor could ever see, is cut.
   `hidden` lines are the pre-Safari-16 fallback for `clip`.
   The body rule is what makes it airtight: `clip` on a non-root box is not a
   scroll container at all, so not even script or a touch swipe can drag the
   layout sideways, while `overflow-y` stays `visible` (clip is the one value
   that pairs with visible without forcing a scroll container). */
html{overflow-x:hidden;overflow-x:clip}
body{overflow-x:hidden;overflow-x:clip;overflow-y:visible}
/* the sticky/fixed chrome and the off-canvas mobile panel are unaffected: fixed
   boxes are not clipped by an ancestor's overflow, only by their containing block */

/* 3. Resilience: if a webfont is unavailable, keep the layout metrics stable */
body{font-family:'Plus Jakarta Sans',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif}
img{max-width:100%}
</style>"""
kb = html.index("</head>")
edits.append((kb, kb, PROD_CSS))
report.append(("style", "mx-prod (font + overflow fix)", "inserted", 0))

# ------------------------------------------------------------------- apply
edits.sort(key=lambda e: e[0])
out, pos = [], 0
for s, e, rep in edits:
    if s < pos:
        sys.exit(f"overlapping edits at {s}")
    out.append(html[pos:s]); out.append(rep); pos = e
out.append(html[pos:])
result = "".join(out)

leftover = re.findall(r'data:image/[a-zA-Z+]+;base64,[A-Za-z0-9+/=]{40,}', result)
assert not leftover, f"{len(leftover)} inlined raster images survived"
svg_uris = len(re.findall(r'data:image/svg\+xml', result))
open(OUT, "w", encoding="utf-8", errors="surrogateescape").write(result)

import os
before, after = os.path.getsize(SRC), os.path.getsize(OUT)
total_assets = sum(f.stat().st_size for f in os.scandir("dist/img")) + os.path.getsize("dist/fonts/plus-jakarta-sans-latin.woff2")
print(f"{'what':<12}{'key':<32}{'value':<44}{'removed':>9}")
for kind, key, val, rm in report[:8]:
    print(f"{kind:<12}{key:<32}{str(val)[:43]:<44}{rm:>9}")
print(f"... {len(report) - 8} more edits (all 52 images + 22 img hints)")
print(f"     inline SVG data URIs kept as-is (tiny, non-raster): {svg_uris}")
print(f"\ndist/index.html: {before/1048576:.2f} MB -> {after/1024:.0f} KB "
      f"({100 - after * 100 / before:.1f}% smaller)")
