"""Export approved image-generation results for the static app.

Usage: python3 tools/import_studio.py logs/generated-inputs.json
The JSON list contains category, id, source (PNG path), and prompt for each item.
Only sizing/alignment and WebP encoding happen here; designs come from imagegen.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/studio'
# Collar meeting points measured on the approved 1122 x 1402 shirt renders.
COLLAR_Y = dict(lblue=225, magenta=194, wine=213, bluedot=195,
                petrol=225, black=225, whitedot=218, beige=210)
SIZES = dict(shirts=(900, 1125), ties=(180, 1125), clips=(720, 60), belts=(528, 320))


def export(item):
    category, ident = item['category'], item['id']
    if category not in SIZES or not ident.isalnum():
        raise ValueError('Unknown category or invalid item id')
    src = Path(item['source'])
    with Image.open(src) as opened:
        if opened.mode != 'RGBA' or opened.getchannel('A').getextrema()[0] != 0:
            raise ValueError(f'{ident} needs a genuinely transparent generated image')
        image = opened.copy()
    if category == 'shirts':
        if image.size != (1122, 1402):
            raise ValueError(f'Recalibrate collar for {ident}: {image.size}')
        scale = 840 / image.width
        image = image.resize((840, round(image.height * scale)), Image.Resampling.LANCZOS)
        out = Image.new('RGBA', SIZES[category])
        out.alpha_composite(image, (30, round(190 - COLLAR_Y[ident] * scale)))
    else:
        # Tight transparent crop gives all variants a common visible size.
        box = image.getchannel('A').point(lambda a: 255 if a > 128 else 0).getbbox()
        if box is None:
            raise ValueError(f'Empty generated image: {ident}')
        image = image.crop(box)
        out = image.resize(SIZES[category], Image.Resampling.LANCZOS)
    dest = OUT / category / f'{ident}.webp'
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, 'WEBP', quality=90, method=6)
    return dict(category=category, id=ident, file=f'{category}/{ident}.webp',
                source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                tool='built-in image_gen', prompt=item['prompt'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    items = json.loads(args.manifest.read_text())
    records = [export(item) for item in items]
    (OUT / 'provenance.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'Exported {len(records)} studio assets to {OUT}')


if __name__ == '__main__':
    main()
