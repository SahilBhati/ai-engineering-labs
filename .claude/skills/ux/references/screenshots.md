# Capturing screenshots (macOS, headless Chrome)

```bash
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$C" --headless=new --disable-gpu --hide-scrollbars --window-size=1600,2400 \
  --virtual-time-budget=6000 --screenshot=out.png "https://example.com/"
```

- Desktop width: 1440–1600 px. Height: tall enough for the full page.
- `--virtual-time-budget` lets scripts and fonts finish before the capture.
- Local files: use a `file://` URL to the HTML.
- **Headless windows can't go below 500 px wide.** A "390 px" screenshot is
  really a 500 px page cropped. For phone checks, load the page in a 390 px
  `<iframe>` inside a 500 px window and add `--allow-file-access-from-files`.
- Find real links before capturing sub-pages: `--dump-dom` the page and read the
  `<header>` / `<nav>` anchors. Never guess URLs.
- Capture every section the brief cares about (e.g. each header tab), not only
  the home page.
- Look once, fix, look once more. Don't loop on screenshots.
