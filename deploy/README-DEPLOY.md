# El Halfawy — deployment guide

## What ships

Upload **the whole contents of `dist/`** as the site root:

```
dist/
  index.html                420 KB raw / 134 KB gzip — the site (app + CSS + markup)
  img/     48 hash-named WebP files, 2.19 MB total (loaded on demand)
  fonts/   plus-jakarta-sans-latin.woff2, 27 KB (one file, self-hosted)
  favicon.ico, favicon-32.png, favicon-16.png, apple-touch-icon.png
  og-image.jpg              1200×630 social preview
  robots.txt, sitemap.xml
```

`elhalfawy-v20.html` in the project root is the **original single-file build and is
left untouched** as the reference copy. `dist/index.html` is the same site, same
markup, same styles, same interactions — only the *delivery* changed.

> `dist/` must be served over HTTP (any static host works). If you open
> `dist/index.html` straight from the file system, browsers block the self-hosted
> webfont, so text falls back to the system font stack. Use a local server
> (`python -m http.server` inside `dist/`) to preview exactly what visitors get.

## Upload

```bash
rsync -a --delete dist/ user@server:/var/www/elhalfawy/
```

Then enable the server block:

```bash
sudo cp deploy/nginx-elhalfawy.conf /etc/nginx/sites-available/elhalfawy
sudo ln -s /etc/nginx/sites-available/elhalfawy /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d elhalfawy.com -d www.elhalfawy.com   # TLS
```

## Verify after every deploy

```bash
curl -sI https://www.elhalfawy.com/ | grep -i -E 'cache-control|content-encoding'
curl -s  -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download} bytes\n' https://www.elhalfawy.com/
curl -sI https://www.elhalfawy.com/img/<any-hash-named-file>.webp | grep -i cache-control
```

- HTML: `content-encoding: gzip`, `cache-control: no-cache, must-revalidate`, ~134 KB
- images/fonts: `cache-control: public, max-age=31536000, immutable`
- open `/` and `/img/…` in a browser, check the console is clean, then walk
  Home → About → Services → Projects → Contact and send one test inquiry from the
  contact form.

## Rollback

The previous build is a single file: keep `elhalfawy-v20.html` next to `dist/`
on the server, or keep the nginx `root` pointing at the old directory. Copying the
old file back as `index.html` restores the previous site immediately (that version
has all images inlined, so nothing else is needed).

## Rebuilding from source

The build is reproducible and scripted — never hand-edit `dist/`:

```bash
python tools/build_images.py       # 52 inlined images -> 48 optimised WebP files
python tools/build_meta_assets.py  # favicon / apple-touch / og-image
python tools/build_html.py         # elhalfawy-v20.html -> dist/index.html
python tools/serve.py 8080         # optional: local production-like preview
```

`dist/img-manifest.json` records every image (original name → output file → bytes)
so a future image swap stays traceable.
