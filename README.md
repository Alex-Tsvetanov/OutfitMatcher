# Fitting Room

Pick a shirt, tie, tie clip and belt, and preview the pieces together.

Live: https://alex-tsvetanov.github.io/OutfitMatcher/

## How it works

- `index.html` is the whole app. No build step and no runtime dependencies.
- `assets/studio/` contains 29 digitally recreated product images: 8 shirts, 12 ties, 6 clips and 3 buckles. Both the cards and outfit preview use these images.
- Shirts share a centered, closed collar; ties, clips and buckles use aligned transparent canvases.
- Faded pieces don't fit the current picks. Picking one anyway removes whatever it clashes with.
- The last outfit is remembered in the browser.

The studio images were made with the built-in image-generation tool using the wardrobe photos as references. They approximate the original colors and patterns; they are not exact fabric scans or measured fit simulations. Final prompts and source PNG hashes are recorded in `assets/studio/provenance.json`.

## Import generated images

Keep approved transparent PNGs locally. Create a JSON list with `category`, `id`, `source` (local PNG path), and `prompt` for each of the 29 items, then run:

```
pip install pillow numpy
python3 tools/import_studio.py /path/to/generated-inputs.json
python3 tools/check_studio.py
```

The importer only aligns, sizes and encodes images as WebP. Shirt collar coordinates in `tools/import_studio.py` are calibrated to the approved renders; recalibrate when replacing those renders. The browser's `.stage` CSS uses the same collar anchor: `(450, 190)` on a `900 × 1125` canvas.

## Original photo assets

The original crops in `assets/shirts/`, `assets/ties/`, `assets/clips/` and `assets/belts/` remain as references. `tools/build_assets.py` rebuilds those crops from an uncommitted `clothes/` directory; it does not overwrite the studio images. Camera originals are excluded because of their size and possible location metadata.
