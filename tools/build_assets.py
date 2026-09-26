"""Cut the real clothes out of the photos in clothes/ and write web assets.

Run:  python tools/build_assets.py [--sheet OUT.png]

Outputs assets/{shirts,ties,clips,belts}/*.webp and assets/geometry.json.
All coordinates below were traced by hand on the source photos.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "clothes"
OUT = ROOT / "assets"

# Physical layout of the close-up preview frame (centimetres).
BLADE_CM = 8.0        # widest part of a tie blade
CLIP_CM = 6.0         # length of a tie clip bar
KNOT_TOP_CM = 3.0     # gap between frame top and knot top
FRAME_ASPECT = 1.0    # width / height
CLIP_AT = 0.70        # clip centre, as a fraction of frame height
FRAME_PX = (900, 900)
THUMB_PX = (320, 400)
PREVIEW_W = 1200      # shirt coordinates below are on a 1200 x 1600 preview

TIE_BLADE_PX = 170    # exported blade width
TIE_PAD = 8

# Shirts. anchor = knot top on the collar, target = a point lower on the placket,
# pxcm = preview pixels per centimetre (from shoulder width and button spacing).
SHIRTS = [
    dict(id="lblue",    file="20260925_175430.jpg", anchor=(568, 445), target=(606, 730), pxcm=19.0),
    dict(id="magenta",  file="20260925_175500.jpg", anchor=(565, 474), target=(582, 702), pxcm=14.1),
    dict(id="wine",     file="20260925_175523.jpg", anchor=(545, 470), target=(545, 800), pxcm=14.5),
    dict(id="bluedot",  file="20260925_175551.jpg", anchor=(560, 440), target=(565, 730), pxcm=16.6),
    dict(id="petrol",   file="20260925_175617.jpg", anchor=(545, 480), target=(545, 800), pxcm=14.5),
    dict(id="black",    file="20260925_175640.jpg", anchor=(575, 440), target=(575, 800), pxcm=15.4),
    dict(id="whitedot", file="20260925_175702.jpg", anchor=(540, 440), target=(540, 800), pxcm=15.6),
    dict(id="beige",    file="20260925_175730.jpg", anchor=(555, 400), target=(560, 700), pxcm=17.0),
]

# Ties: outlines traced on 3x zoom sheets of ties.webp, in sheet pixels.
TIE_ROWS = [(0, 282), (282, 563), (563, 800)]
TIE_XS = [27, 213, 400, 586, 772]
TIE_ZOOM = 3
TIES = {
    "burg":    (0, 0, [(130,10),(293,10),(328,55),(258,222),(284,300),(318,400),(330,500),(330,600),(322,700),(312,846),(110,846),(100,700),(92,600),(88,500),(97,420),(120,330),(148,222),(97,62)]),
    "navy":    (0, 0, [(792,38),(948,40),(992,95),(915,262),(945,350),(970,430),(985,520),(990,600),(985,700),(975,846),(725,846),(718,700),(712,600),(710,520),(725,430),(760,350),(805,262),(737,100)]),
    "geo":     (0, 1, [(300,28),(470,8),(517,90),(447,262),(480,350),(505,430),(515,520),(512,600),(505,700),(495,846),(305,846),(290,700),(275,600),(265,520),(280,430),(320,340),(372,258),(268,80)]),
    "silver":  (0, 1, [(808,45),(900,40),(968,84),(905,232),(940,330),(962,430),(968,520),(958,600),(940,700),(920,846),(815,846),(795,700),(775,600),(765,520),(768,430),(785,330),(818,232),(776,68)]),
    "nstripe": (1, 0, [(152,72),(240,58),(315,98),(336,150),(248,318),(268,400),(282,480),(292,560),(300,640),(300,720),(292,843),(100,843),(75,720),(60,640),(55,560),(65,480),(90,400),(128,305),(93,110)]),
    "bw":      (1, 0, [(803,98),(880,70),(955,93),(980,150),(905,300),(930,400),(950,480),(955,560),(955,640),(945,720),(930,843),(760,843),(740,720),(728,620),(725,540),(735,460),(760,380),(797,292),(755,130)]),
    "char":    (1, 1, [(312,95),(420,66),(535,99),(544,118),(465,280),(495,380),(515,460),(520,540),(515,620),(505,720),(495,843),(310,843),(300,720),(290,620),(285,540),(293,460),(310,380),(335,285),(283,125)]),
    "dots":    (1, 1, [(765,85),(860,60),(952,88),(910,248),(935,340),(955,420),(960,500),(950,600),(930,720),(910,843),(785,843),(770,720),(758,600),(755,500),(765,420),(785,340),(810,250)]),
    "turq":    (2, 0, [(237,33),(340,30),(368,75),(300,212),(340,300),(362,380),(368,450),(365,540),(350,640),(335,711),(215,711),(195,640),(175,540),(172,450),(182,380),(205,300),(238,212),(200,70)]),
    "lbs":     (2, 0, [(822,30),(945,42),(975,85),(875,205),(905,300),(920,380),(922,460),(915,560),(905,640),(890,711),(770,711),(745,640),(725,560),(722,460),(735,380),(760,300),(795,205),(755,82)]),
    "purple":  (2, 1, [(250,25),(345,30),(380,70),(320,200),(345,300),(358,380),(360,460),(355,560),(345,640),(335,711),(215,711),(200,640),(185,560),(180,460),(185,380),(205,280),(225,198),(190,60)]),
    "gdots":   (2, 1, [(822,52),(908,56),(938,95),(880,220),(915,300),(935,380),(940,460),(932,560),(915,640),(900,711),(785,711),(770,640),(755,560),(750,460),(755,380),(775,300),(800,218),(766,84)]),
}

# Clips: bar end centres and bar thickness on clips.webp (upper-left end first).
CLIPS = {
    "blue":   ((134, 592), (452, 948), 40),
    "black":  ((230, 496), (548, 845), 40),
    "red":    ((324, 386), (656, 733), 40),
    "silver": ((440, 280), (758, 640), 40),
    "gun":    ((538, 170), (848, 512), 40),
    "gold":   ((670, 66),  (976, 408), 40),
}

# Belt buckles: face corners on belts.webp, clockwise from top-left.
BELTS = {
    "chrome": [(356.7, 105.3), (618.7, 252.0), (513.3, 376.7), (248.0, 216.7)],
    "gun":    [(186.7, 298.7), (500.0, 380.0), (440.0, 523.3), (108.0, 420.0)],
    "rose":   [(100.0, 516.7), (448.0, 538.7), (421.3, 703.3), (63.3, 670.0)],
}
BUCKLE_PX = (330, 200)


def row_extents(alpha):
    """Left, right and width of opaque pixels per row (None for empty rows)."""
    on = alpha > 127
    rows = []
    for y in range(on.shape[0]):
        xs = np.flatnonzero(on[y])
        rows.append((xs[0], xs[-1], xs[-1] - xs[0] + 1) if xs.size else None)
    return rows


def tie_axis(alpha):
    """Neck centre and bottom centre of a tie mask."""
    rows = row_extents(alpha)
    ys = [y for y, r in enumerate(rows) if r]
    top, bot = ys[0], ys[-1]
    length = bot - top
    band = [y for y in ys if top + 0.15 * length <= y <= top + 0.5 * length]
    neck = min(band, key=lambda y: rows[y][2])
    neck_c = ((rows[neck][0] + rows[neck][1]) / 2, neck)
    tail = [(rows[y][0] + rows[y][1]) / 2 for y in ys[-8:]]
    return neck_c, (sum(tail) / len(tail), bot), rows, top, neck


NO_PEEL = {"silver"}  # light fabric reads as collar white


def peel_collar(rgb, mask, depth):
    """Remove white shirt-collar pixels that touch the outline of the knot.

    Peels inward from transparent pixels, one pixel ring per pass, and only
    through near-white pixels in the top part of the tie.
    """
    px = np.asarray(rgb).astype(np.int16)
    lo, hi = px.min(-1), px.max(-1)
    white = (lo > 200) & (hi - lo < 28)
    alpha = np.asarray(mask).astype(np.float32)
    inside = alpha > 20
    ys = np.flatnonzero(inside.any(1))
    knot_rows = np.zeros_like(inside)
    knot_rows[: ys[0] + int(0.35 * (ys[-1] - ys[0]))] = True
    killed = np.zeros_like(inside)
    for _ in range(depth):
        out = ~inside
        near = np.zeros_like(out)
        near[1:] |= out[:-1]; near[:-1] |= out[1:]
        near[:, 1:] |= out[:, :-1]; near[:, :-1] |= out[:, 1:]
        step = inside & near & white & knot_rows
        if not step.any():
            break
        killed |= step
        inside &= ~step
    soft = Image.fromarray((killed * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    soft = np.asarray(soft.filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    return Image.fromarray((alpha * (1 - soft)).clip(0, 255).astype(np.uint8))


def build_tie(sheet, tid):
    r, p, pts = TIES[tid]
    x0, y0 = TIE_XS[p * 2], TIE_ROWS[r][0]
    poly = [(x0 + x / TIE_ZOOM, y0 + y / TIE_ZOOM) for x, y in pts]
    bx0 = math.floor(min(x for x, _ in poly)) - 4
    by0 = max(0, math.floor(min(y for _, y in poly)) - 4)
    bx1 = math.ceil(max(x for x, _ in poly)) + 4
    by1 = min(sheet.height, math.ceil(max(y for _, y in poly)))
    up, ss = 3, 4
    rgb = sheet.crop((bx0, by0, bx1, by1))
    rgb = rgb.resize((rgb.width * up, rgb.height * up), Image.LANCZOS)
    big = Image.new("L", (rgb.width * ss, rgb.height * ss), 0)
    big_poly = [((x - bx0) * up * ss, (y - by0) * up * ss) for x, y in poly]
    ImageDraw.Draw(big).polygon(big_poly, fill=255)
    big = big.filter(ImageFilter.MinFilter(13))  # pull the edge ~0.5 source px inside
    mask = big.resize(rgb.size, Image.LANCZOS)
    if tid not in NO_PEEL:
        mask = peel_collar(rgb, mask, depth=3 * up)
    tie = rgb.convert("RGBA")
    tie.putalpha(mask)

    neck, bottom, _, _, _ = tie_axis(np.asarray(mask))
    lean = math.degrees(math.atan2(bottom[0] - neck[0], bottom[1] - neck[1]))
    tie = tie.rotate(-lean, resample=Image.BICUBIC, expand=True, center=None)

    alpha = np.asarray(tie.getchannel("A"))
    neck, bottom, rows, top, neck_y = tie_axis(alpha)
    ys = [y for y, rr in enumerate(rows) if rr]
    # ignore the last rows: rotation leaves a slanted cut there
    blade = max(rows[y][2] for y in ys if neck_y < y < ys[-1] - 12)
    cx = neck[0]
    scale = TIE_BLADE_PX / blade
    half = TIE_BLADE_PX / 2 + TIE_PAD
    margin = 60
    padded = Image.new("RGBA", (tie.width + 2 * margin, tie.height), (0, 0, 0, 0))
    padded.paste(tie, (margin, 0))
    box = (cx - half / scale + margin, top, cx + half / scale + margin, ys[-1] - 12)
    out_w = round(2 * half)
    out_h = round((box[3] - box[1]) * scale)
    tie = padded.resize((out_w, out_h), Image.LANCZOS, box=box)
    return tie, dict(lean=round(lean, 2), lenBlades=round(out_h / TIE_BLADE_PX, 3))


def build_clip(sheet, cid):
    (x0, y0), (x1, y1), thick = CLIPS[cid]
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    length = math.hypot(x1 - x0, y1 - y0)
    rot = sheet.rotate(ang, resample=Image.BICUBIC, center=(cx, cy), fillcolor=(255, 255, 255))
    pad = 4
    box = (round(cx - length / 2 - pad), round(cy - thick / 2 - pad),
           round(cx + length / 2 + pad), round(cy + thick / 2 + pad))
    bar = rot.crop(box).convert("RGBA")
    ss = 4
    m = Image.new("L", (bar.width * ss, bar.height * ss), 0)
    inset = 1.5
    ImageDraw.Draw(m).rounded_rectangle(
        [(pad + inset) * ss, (pad + inset) * ss,
         (bar.width - pad - inset) * ss, (bar.height - pad - inset) * ss],
        radius=5 * ss, fill=255)
    bar.putalpha(m.resize(bar.size, Image.LANCZOS))
    return bar.crop((pad, pad, bar.width - pad, bar.height - pad))


def perspective_coeffs(dst, src):
    """Coefficients mapping output (dst) points to input (src) points."""
    a = []
    b = []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.lstsq(np.array(a, float), np.array(b, float), rcond=None)[0].tolist()


def build_belt(sheet, bid):
    w, h = BUCKLE_PX
    ss = 3
    coeffs = perspective_coeffs([(0, 0), (w * ss, 0), (w * ss, h * ss), (0, h * ss)], BELTS[bid])
    big = sheet.resize(sheet.size, Image.LANCZOS)
    face = big.transform((w * ss, h * ss), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)
    return face.resize((w, h), Image.LANCZOS)


def load_shirt(name):
    im = Image.open(SRC / name)
    if max(im.size) > 9000:
        im.draft("RGB", (im.width // 2, im.height // 2))
    im = ImageOps.exif_transpose(im.convert("RGB"))
    return im


def build_shirt(s, frame_w_cm, frame_h_cm):
    im = load_shirt(s["file"])
    f = im.width / PREVIEW_W
    ax, ay = s["anchor"][0] * f, s["anchor"][1] * f
    tx, ty = s["target"][0] * f, s["target"][1] * f
    lean = math.degrees(math.atan2(tx - ax, ty - ay))
    pxcm = s["pxcm"] * f
    fw, fh = frame_w_cm * pxcm, frame_h_cm * pxcm
    reach = math.hypot(fw, fh) + 10
    region = (round(ax - reach), round(ay - reach), round(ax + reach), round(ay + reach))
    crop = im.crop(region)
    cax, cay = ax - region[0], ay - region[1]
    crop = crop.rotate(-lean, resample=Image.BICUBIC, center=(cax, cay))
    left, top = cax - fw / 2, cay - KNOT_TOP_CM * pxcm
    close = crop.crop((round(left), round(top), round(left + fw), round(top + fh)))
    close = close.resize(FRAME_PX, Image.LANCZOS)

    tw = 60 * pxcm
    th = tw * THUMB_PX[1] / THUMB_PX[0]
    tbox = (round(ax - tw / 2), round(ay - 13 * pxcm), round(ax + tw / 2), round(ay - 13 * pxcm + th))
    thumb = im.crop(tbox).resize(THUMB_PX, Image.LANCZOS)
    return close, thumb, round(lean, 2)


def save(img, path, quality=82):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=quality, method=6)


def main():
    sheet_out = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    geo = {"ties": {}, "shirts": {}}

    ties_img = Image.open(SRC / "ties.webp").convert("RGB")
    tie_imgs = {}
    for tid in TIES:
        tie, meta = build_tie(ties_img, tid)
        tie_imgs[tid] = tie
        geo["ties"][tid] = meta
        save(tie, OUT / "ties" / f"{tid}.webp", 88)

    shortest = min(m["lenBlades"] for m in geo["ties"].values())
    frame_h = KNOT_TOP_CM + shortest * BLADE_CM - 0.3
    frame_w = frame_h * FRAME_ASPECT
    geo["frame"] = dict(wcm=round(frame_w, 3), hcm=round(frame_h, 3), knotTopCm=KNOT_TOP_CM,
                        bladeCm=BLADE_CM, clipCm=CLIP_CM, clipAt=CLIP_AT,
                        tieImgW=TIE_BLADE_PX + 2 * TIE_PAD, tieBladePx=TIE_BLADE_PX)

    clips_img = Image.open(SRC / "clips.webp").convert("RGB")
    clip_imgs = {cid: build_clip(clips_img, cid) for cid in CLIPS}
    for cid, im in clip_imgs.items():
        save(im, OUT / "clips" / f"{cid}.webp", 90)

    belts_img = Image.open(SRC / "belts.webp").convert("RGB")
    belt_imgs = {bid: build_belt(belts_img, bid) for bid in BELTS}
    for bid, im in belt_imgs.items():
        save(im, OUT / "belts" / f"{bid}.webp", 88)

    shirt_imgs = {}
    for s in SHIRTS:
        close, thumb, lean = build_shirt(s, frame_w, frame_h)
        shirt_imgs[s["id"]] = (close, thumb)
        geo["shirts"][s["id"]] = dict(lean=lean)
        save(close, OUT / "shirts" / f"{s['id']}.webp", 80)
        save(thumb, OUT / "shirts" / f"{s['id']}-thumb.webp", 80)
        print("shirt", s["id"], "lean", lean)

    (OUT / "geometry.json").write_text(json.dumps(geo, indent=1))
    print(json.dumps(geo["frame"]), {k: v["lenBlades"] for k, v in geo["ties"].items()})

    if sheet_out:
        contact_sheet(sheet_out, geo, shirt_imgs, tie_imgs, clip_imgs, belt_imgs)


def compose(close, tie, clip, frame):
    """Same layout the page uses, rendered in Python for checking."""
    W, H = close.size
    opc = W / frame["wcm"]
    out = close.convert("RGBA")
    tw = round(frame["tieImgW"] / frame["tieBladePx"] * BLADE_CM * opc)
    th = round(tie.height * tw / tie.width)
    t = tie.resize((tw, th), Image.LANCZOS)
    out.alpha_composite(t, (round(W / 2 - tw / 2), round(KNOT_TOP_CM * opc)))
    cw = round(CLIP_CM * opc)
    ch = round(clip.height * cw / clip.width)
    c = clip.resize((cw, ch), Image.LANCZOS)
    out.alpha_composite(c, (round(W / 2 - cw / 2), round(H * CLIP_AT - ch / 2)))
    return out.convert("RGB")


def contact_sheet(path, geo, shirts, ties, clips, belts):
    tids, cids = list(ties), list(clips)
    tiles = []
    for i, (sid, (close, thumb)) in enumerate(shirts.items()):
        tiles.append(compose(close, ties[tids[i % len(tids)]], clips[cids[i % len(cids)]], geo["frame"]))
    for j in range(8, 12):
        tiles.append(compose(list(shirts.values())[j % 8][0], ties[tids[j]], clips[cids[j % 6]], geo["frame"]))
    tw, th = 300, 300
    sheet = Image.new("RGB", (tw * 6, th * 2 + 420), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t.resize((tw, th), Image.LANCZOS), ((i % 6) * tw, (i // 6) * th))
    y = th * 2 + 10
    x = 10
    for sid, (_, thumb) in shirts.items():
        sheet.paste(thumb.resize((160, 200)), (x, y)); x += 165
    y += 210
    x = 10
    for tie in ties.values():
        t = tie.resize((50, round(tie.height * 50 / tie.width)))
        bg = Image.new("RGB", t.size, (128, 128, 128)); bg.paste(t, mask=t.getchannel("A"))
        sheet.paste(bg, (x, y)); x += 56
    x += 10
    for c in clips.values():
        cc = c.resize((200, round(c.height * 200 / c.width)))
        bg = Image.new("RGB", cc.size, (128, 128, 128)); bg.paste(cc, mask=cc.getchannel("A"))
        sheet.paste(bg, (x, y)); y += 30
    x += 210; y = th * 2 + 220
    for b in belts.values():
        sheet.paste(b.resize((165, 100)), (x, y)); y += 105
    sheet.save(path)


if __name__ == "__main__":
    main()
