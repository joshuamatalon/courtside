"""Generate Courtside app icons. Run: python tools/make_icons.py

The mark is the six-zone court with Zone 1 - the serving spot - lit up.
It is the app's one signature visual and it reads at 40px, which matters
because it will sit on a home screen next to Pass Chart's ribbon mark and
the two must never be confused.
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
os.makedirs(OUT, exist_ok=True)

BG = (10, 12, 17)
ZONE_BACK = (34, 40, 52)
ZONE_FRONT = (52, 60, 76)
SERVER = (47, 208, 138)
NET = (78, 123, 242)


def icon(size, maskable=False):
    img = Image.new("RGBA", (size, size), BG + (255,))
    d = ImageDraw.Draw(img)

    pad = size * (0.27 if maskable else 0.17)
    w = size - 2 * pad
    gap = size * 0.028
    cw = (w - 2 * gap) / 3.0
    ch = (w - gap) / 2.0
    radius = max(2, int(cw * 0.16))

    # net line across the top edge of the front row
    net_y = pad - size * 0.055
    d.rounded_rectangle(
        [pad, net_y - size * 0.012, pad + w, net_y + size * 0.012],
        radius=size * 0.012, fill=NET + (255,),
    )

    for row in range(2):           # row 0 = front (at the net), row 1 = back
        for col in range(3):
            x0 = pad + col * (cw + gap)
            y0 = pad + row * (ch + gap)
            # zone 1 is back row, right-hand column - the serving spot
            is_server = (row == 1 and col == 2)
            fill = SERVER if is_server else (ZONE_FRONT if row == 0 else ZONE_BACK)
            d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=radius, fill=fill + (255,))
    return img


for size in (192, 512):
    icon(size).save(os.path.join(OUT, "icon-%d.png" % size))
icon(512, maskable=True).save(os.path.join(OUT, "maskable-512.png"))
icon(180).convert("RGB").save(os.path.join(OUT, "apple-touch-icon.png"))

for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print("%-24s %6d bytes  %s" % (f, os.path.getsize(p), Image.open(p).size))
