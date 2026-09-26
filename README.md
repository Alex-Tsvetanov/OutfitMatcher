# Fitting Room

Pick a shirt, tie, tie clip and belt, and see the real pieces together.

Live: https://alex-tsvetanov.github.io/OutfitMatcher/

## How it works

- `index.html` is the whole app. No build step and no dependencies.
- `assets/` holds images cut from the original wardrobe photos: shirt close-ups and thumbnails, ties, clips and belt buckles.
- Faded pieces don't fit the current picks. Picking one anyway removes whatever it clashes with.
- The last outfit is remembered in the browser.

## Rebuild the images

The original photos live in `clothes/`, which is not committed. They are large and camera files can carry location metadata.

```
pip install pillow numpy
python tools/build_assets.py --sheet check.png
```

Tie outlines, clip positions, buckle corners and each shirt's knot point are traced by hand at the top of `tools/build_assets.py`. A new photo needs its coordinates added there. `check.png` is a contact sheet for checking the cutouts.
