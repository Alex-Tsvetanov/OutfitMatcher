"""Check the generated wardrobe: python3 tools/check_studio.py."""
import json
from pathlib import Path
from PIL import Image
from import_studio import SIZES

root = Path(__file__).resolve().parent.parent
studio = root / 'assets/studio'
expected = {
    'shirts': 'lblue magenta wine bluedot petrol black whitedot beige',
    'ties': 'burg navy geo silver nstripe bw char dots turq lbs purple gdots',
    'clips': 'blue black red silver gun gold',
    'belts': 'chrome gun rose',
}
records = json.loads((studio / 'provenance.json').read_text())
assert len(records) == 29, 'Missing generated items or duplicate provenance'
assert {(r['category'], r['id']) for r in records} == {
    (category, ident) for category, ids in expected.items() for ident in ids.split()
}
for category, ids in expected.items():
    for ident in ids.split():
        path = studio / category / f'{ident}.webp'
        with Image.open(path) as image:
            assert image.size == SIZES[category], f'Unaligned canvas: {path}'
            assert image.mode == 'RGBA', f'Missing transparency: {path}'
            lo, hi = image.getchannel('A').getextrema()
            assert lo == 0 and hi >= 240, f'Empty or opaque backdrop: {path}'
            if category == 'shirts':
                # The shared knot point must land on the buttoned shirt.
                assert image.getpixel((450, 205))[3] > 240, path
            if category == 'ties':
                alpha = image.getchannel('A')
                # Knot, neck and pointed blade remain centered and connected.
                for y in [20, 160, 400, 800, 1090]:
                    assert alpha.getpixel((90, y)) > 200, (path, y)
                assert alpha.getpixel((3, 1100)) < 20, f'Tie tip is clipped: {path}'
page = (root / 'index.html').read_text()
for category in expected:
    assert f'assets/studio/{category}/' in page, f'App still uses original {category}'
assert 'const GEO=' not in page, 'Old close-up photo calibration is still active'
print('PASS: all 29 studio assets, transparency, shared dimensions, collar/tie anchors and app references')
