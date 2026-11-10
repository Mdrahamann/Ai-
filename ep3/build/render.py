"""Render Episode 3, Milo and the Missing Cookie (6:00, 1920x1080, 24 fps), from ../plan.py and out/lines.json.

Milo and Pip are the pose cutouts from Episode 1 (ep1/build/cutouts); Mr. Bumble is cut from characters/ (build/cutouts).
The kitchen, cookie tray, flour, captions and icons are drawn here; the scene engine is the same as Episode 2.
Usage: python3 audio.py && python3 render.py  (python3 render.py S14 S15 renders single shots)
"""
import os, sys, json, math, subprocess, functools
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import plan
plan.check()
SH = {s["id"]: s for s in plan.SHOTS}
OUT = os.path.join(HERE, "out"); SEG = os.path.join(OUT, "segments"); os.makedirs(SEG, exist_ok=True)
CUT = os.path.join(HERE, "..", "..", "ep1", "build", "cutouts")
FONT = os.path.join(HERE, "..", "..", "ep1", "build", "fonts", "Fredoka.ttf")
LINES = json.load(open(os.path.join(OUT, "lines.json")))
W, H, FPS = 1920, 1080, 24

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def ramp(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)

# ------------------------------------------------------------------ sprites
@functools.lru_cache(None)
def sprite(pose, h, flip=False, tint=0):
    local = os.path.join(HERE, "cutouts", pose + ".png")
    im = Image.open(local if os.path.exists(local) else os.path.join(CUT, pose + ".png")).convert("RGBA")
    im = im.resize((max(1, round(im.width * h / im.height)), int(h)), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if tint < 0:  # guilt / sadness: cooler, a little gray
        a = -tint / 10
        r, g, b, al = im.split()
        r = r.point(lambda v: int(v * (1 - 0.18 * a))); g = g.point(lambda v: int(v * (1 - 0.1 * a)))
        b = b.point(lambda v: min(255, int(v * (1 + 0.08 * a))))
        im = Image.merge("RGBA", (r, g, b, al))
    elif tint:  # frustration: warmer, redder
        a = tint / 10
        r, g, b, al = im.split()
        g = g.point(lambda v: int(v * (1 - 0.22 * a))); b = b.point(lambda v: int(v * (1 - 0.3 * a)))
        r = r.point(lambda v: min(255, int(v * (1 + 0.04 * a))))
        im = Image.merge("RGBA", (r, g, b, al))
    return im

# ------------------------------------------------------------------ drawing
def gradient(w, h, top, low):
    t = np.linspace(0, 1, h)[:, None, None]
    a = (np.array(top)[None, None] * (1 - t) + np.array(low)[None, None] * t).astype(np.uint8)
    return Image.fromarray(np.repeat(a, w, 1), "RGB")

def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size); f.set_variation_by_name(weight); return f

def sparkle(d, x, y, r, a=255, col=(255, 255, 255)):
    d.polygon([(x, y - r), (x + r * .22, y - r * .22), (x + r, y), (x + r * .22, y + r * .22), (x, y + r),
               (x - r * .22, y + r * .22), (x - r, y), (x - r * .22, y - r * .22)], fill=col + (int(a),))

def caption(im, text, hi, t, t0, t1, pos="low"):
    if not (t0 <= t <= t1): return
    a = min(1, (t - t0) / 0.25, (t1 - t) / 0.25)
    f = font(64 if pos != "tag" else 46)
    d0 = ImageDraw.Draw(im)
    tw = d0.textlength(text, font=f)
    padx, h = 46, 104 if pos != "tag" else 78
    cx = W / 2; cy = {"low": 900, "tag": 80, "mid": 540, "top": 120}[pos]
    sc = 0.85 + 0.15 * ease((t - t0) / 0.25)
    L = Image.new("RGBA", (int(tw + padx * 2 + 20), h + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle((10, 10, 10 + tw + padx * 2, 10 + h), radius=h // 2, fill=(255, 248, 235, 240), outline=(235, 200, 160), width=4)
    x = 10 + padx; y = 10 + (h - f.size) / 2 - 6
    for word in text.split(" "):
        col = (235, 110, 40) if word.strip(".!").upper() in hi else (70, 55, 50)
        d.text((x, y), word, font=f, fill=col); x += d.textlength(word + " ", font=f)
    L = L.resize((int(L.width * sc), int(L.height * sc)), Image.BICUBIC)
    L.putalpha(L.getchannel("A").point(lambda v: int(v * a)))
    im.paste(L, (int(cx - L.width / 2), int(cy - L.height / 2)), L)

def bang(d, x, y, t, t0, dur=1.6):
    if not (t0 <= t <= t0 + dur): return
    p = (t - t0); s = 46 * min(1, p / 0.15) * (1 + 0.1 * math.sin(p * 20) * math.exp(-p * 4))
    d.ellipse((x - s, y - s, x + s, y + s), fill=(245, 140, 50, 245))
    d.rounded_rectangle((x - s * 0.13, y - s * 0.6, x + s * 0.13, y + s * 0.18), radius=int(s * 0.1) + 1, fill=(255, 255, 255))
    d.ellipse((x - s * 0.14, y + s * 0.3, x + s * 0.14, y + s * 0.58), fill=(255, 255, 255))

def thought(d, x, y, t, t0):
    if t < t0: return
    for i, (dx, dy, r) in enumerate([(-60, 110, 12), (-35, 70, 20)]):
        d.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill=(255, 255, 255, 235))
    d.rounded_rectangle((x - 20, y - 70, x + 200, y + 40), radius=55, fill=(255, 255, 255, 240))
    for k in range(3):
        on = ((t - t0) * 1.6 - k) % 3 > 0
        if (t - t0) * 1.6 > k:
            d.ellipse((x + 30 + k * 55 - 13, y - 28, x + 30 + k * 55 + 13, y - 2), fill=(90, 80, 80) if on else (180, 170, 170))

def puff_lines(d, x, y, t, strength):
    if strength <= 0: return
    for k in range(3):
        a = math.radians(-60 + k * 30); r0 = 30 + 8 * math.sin(t * 12 + k)
        d.line((x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * (r0 + 40), y + math.sin(a) * (r0 + 40)), fill=(235, 90, 60, int(230 * strength)), width=7)

# ------------------------------------------------------------------ kitchen set and props
WALL0, WALL1 = (205, 230, 246), (186, 214, 238)
STAR = (255, 205, 80); STAR_EDGE = (220, 150, 50); ICING = (255, 236, 120)

@functools.lru_cache(None)
def kitchen(table=True):
    im = gradient(W, H, WALL0, WALL1); d = ImageDraw.Draw(im)
    # door on the far left
    d.rectangle((0, 180, 170, 830), fill=(240, 236, 228)); d.rectangle((0, 200, 150, 830), fill=(150, 200, 230))
    d.ellipse((115, 500, 140, 525), fill=(250, 210, 90))
    # window + sill
    d.rectangle((260, 140, 760, 520), fill=(255, 255, 252)); d.rectangle((285, 165, 735, 495), fill=(190, 228, 250))
    d.ellipse((560, 200, 680, 320), fill=(255, 244, 190))
    d.line((510, 165, 510, 495), fill=(255, 255, 252), width=14); d.line((285, 330, 735, 330), fill=(255, 255, 252), width=14)
    d.rectangle((235, 515, 785, 545), fill=(255, 255, 255), outline=(215, 225, 235))
    # wall clock
    d.ellipse((930, 120, 1070, 260), fill=(255, 255, 255), outline=(120, 150, 180), width=8)
    d.line((1000, 190, 1000, 140), fill=(80, 90, 110), width=6); d.line((1000, 190, 1035, 205), fill=(80, 90, 110), width=6)
    # shelf with jars
    d.rectangle((1230, 300, 1700, 318), fill=(200, 150, 100))
    for i, c in enumerate([(240, 200, 120), (230, 120, 110), (150, 200, 150)]):
        d.rounded_rectangle((1270 + i * 140, 210, 1360 + i * 140, 300), radius=14, fill=c + (255,), outline=(255, 255, 255), width=4)
    # floor tiles
    for row in range(5):
        y0 = 800 + row * 56
        for col in range(0, 26):
            x0 = col * 80 - (row % 2) * 40
            d.rectangle((x0, y0, x0 + 80, y0 + 56), fill=(250, 244, 230) if (col + row) % 2 else (215, 232, 245))
    # counter + oven on the right
    d.rectangle((1180, 600, W, 640), fill=(215, 160, 105)); d.rectangle((1180, 640, W, 820), fill=(235, 205, 165))
    for x in (1200, 1380):
        d.rounded_rectangle((x, 660, x + 160, 800), radius=10, outline=(210, 175, 130), width=5)
        d.ellipse((x + 70, 720, x + 90, 740), fill=(190, 150, 100))
    d.rounded_rectangle((1560, 560, 1880, 820), radius=40, fill=(252, 252, 250), outline=(200, 205, 215), width=6)
    d.ellipse((1650, 620, 1790, 760), fill=(70, 70, 85)); d.ellipse((1665, 635, 1775, 745), fill=(110, 90, 80))
    for k in range(3): d.ellipse((1610 + k * 110, 575, 1640 + k * 110, 600), fill=(220, 120, 90))
    # bowl and flour tin on the counter
    d.chord((1230, 520, 1390, 640), 0, 180, fill=(240, 150, 120)); d.ellipse((1230, 560, 1390, 600), fill=(255, 245, 225))
    d.rounded_rectangle((1420, 500, 1510, 605), radius=14, fill=(200, 210, 225), outline=(150, 160, 180), width=4)
    if table:
        tbl(d)
    return im

def tbl(d, x=760, y=860, r=300):
    d.rectangle((x - 18, y, x + 18, y + 210), fill=(170, 115, 70))
    d.ellipse((x - r, y - r * 0.2, x + r, y + r * 0.2), fill=(185, 125, 75))
    d.ellipse((x - r * 0.97, y - r * 0.22, x + r * 0.97, y + r * 0.15), fill=(215, 160, 100))

@functools.lru_cache(None)
def counter_front():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle((1180, 780, W, 820), fill=(215, 160, 105)); d.rectangle((1180, 820, W, H), fill=(235, 205, 165))
    for x in (1220, 1450, 1680):
        d.rounded_rectangle((x, 850, x + 190, 1060), radius=12, outline=(210, 175, 130), width=6)
    return L

@functools.lru_cache(None)
def table_front():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle((300, 900, 1620, H), fill=(170, 115, 70))
    d.ellipse((260, 780, 1660, 980), fill=(190, 130, 80)); d.ellipse((280, 772, 1640, 960), fill=(215, 160, 100))
    return L

def star(d, x, y, r, rot=0.0, lop=False, glow=0.0):
    pts = []
    for k in range(10):
        a = math.radians(-90 + k * 36 + rot)
        rr = r if k % 2 == 0 else r * 0.48
        if lop and k in (0, 2): rr *= 1.22 if k == 0 else 0.8
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    if glow > 0:
        d.ellipse((x - r * 1.5, y - r * 1.5, x + r * 1.5, y + r * 1.5), fill=(255, 250, 200, int(120 * glow)))
    d.polygon(pts, fill=STAR, outline=STAR_EDGE, width=max(2, int(r * 0.08)))
    d.ellipse((x - r * 0.25, y - r * 0.25, x + r * 0.25, y + r * 0.25), fill=ICING)
    for k in range(3):
        a = k * 2.1 + x
        d.ellipse((x + math.cos(a) * r * 0.45 - 2, y + math.sin(a) * r * 0.45 - 2, x + math.cos(a) * r * 0.45 + 3, y + math.sin(a) * r * 0.45 + 3), fill=(255, 255, 255))

def tray(d, x, y, s, state="eleven", hi=-1, lop_in=1.0, glow=0.0):
    """x,y center; s = scale (1 = 300 px wide). state twelve|eleven|full. hi = index being counted (0..11)."""
    w, h = 300 * s, 210 * s
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=int(18 * s), fill=(200, 205, 215), outline=(150, 155, 170), width=max(2, int(5 * s)))
    d.rounded_rectangle((x - w / 2 + 10 * s, y - h / 2 + 10 * s, x + w / 2 - 10 * s, y + h / 2 - 10 * s), radius=int(12 * s), fill=(225, 228, 235))
    for i in range(12):
        row, col = divmod(i, 4)
        cx = x - w / 2 + (col + 0.5) * w / 4; cy = y - h / 2 + (row + 0.5) * h / 3
        if i == 11 and state == "eleven":
            for k in range(5):
                d.ellipse((cx - 18 * s + k * 9 * s, cy + (k % 2) * 8 * s, cx - 12 * s + k * 9 * s, cy + 6 * s + (k % 2) * 8 * s), fill=(210, 160, 80))
            continue
        if i == 11 and state == "full":
            if lop_in < 1:
                star(d, cx, cy - (1 - lop_in) * 260 * s, 30 * s, 8, True)
            else:
                star(d, cx, cy, 30 * s, 8, True, glow)
            continue
        star(d, cx, cy, 30 * s, (i * 7) % 12 - 6, False, 1.0 if i == hi else 0.0)

def crumbs(d, x, y, s=1.0):
    for k in range(6):
        d.ellipse((x + (k * 17 % 40 - 20) * s, y + (k * 11 % 24 - 12) * s, x + (k * 17 % 40 - 14) * s, y + (k * 11 % 24 - 6) * s), fill=(205, 150, 70))

def flour_face(d, x, y, r, a=1.0):
    for k in range(9):
        ang = k * 0.7; rr = r * (0.55 + 0.1 * (k % 3))
        d.ellipse((x + math.cos(ang) * r * 0.35 - rr, y + math.sin(ang) * r * 0.25 - rr * 0.8, x + math.cos(ang) * r * 0.35 + rr, y + math.sin(ang) * r * 0.25 + rr * 0.8),
                  fill=(255, 255, 255, int(60 * a)))

def poof(d, x, y, t, t0, size=300):
    p = t - t0
    if p < 0 or p > 2.0: return
    for k in range(18):
        ang = k * 2.4; dist = size * min(1, p * 2.5) * (0.3 + 0.7 * ((k * 37) % 10) / 10)
        r = size * 0.22 * (1 + p)
        a = int(200 * max(0, 1 - p / 2.0))
        d.ellipse((x + math.cos(ang) * dist - r, y + math.sin(ang) * dist * 0.7 - r, x + math.cos(ang) * dist + r, y + math.sin(ang) * dist * 0.7 + r), fill=(255, 255, 255, a))

def dust(d, x, y, h):
    """flour specks on a character after the sneeze"""
    for k in range(22):
        dx = ((k * 53) % 100 - 50) / 100 * h * 0.5; dy = -((k * 37) % 100) / 100 * h * 0.95
        r = 6 + k % 5
        d.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill=(255, 255, 255, 210))

def icing_bag(d, x, y, s=1.0):
    d.polygon([(x - 50 * s, y - 70 * s), (x + 50 * s, y - 70 * s), (x, y + 70 * s)], fill=(255, 255, 255), outline=(200, 200, 210))
    d.polygon([(x - 12 * s, y + 40 * s), (x + 12 * s, y + 40 * s), (x, y + 72 * s)], fill=ICING)

def paper_list(d, x, y, s=1.0):
    d.rounded_rectangle((x - 60 * s, y - 80 * s, x + 60 * s, y + 80 * s), radius=8, fill=(255, 255, 250), outline=(200, 190, 175), width=3)
    for k in range(6): d.line((x - 40 * s, y - 55 * s + k * 24 * s, x + 40 * s, y - 55 * s + k * 24 * s), fill=(140, 150, 200), width=4)

def flour_tin(d, x, y, ang=0.0, s=1.0):
    L = Image.new("RGBA", (int(220 * s), int(220 * s)), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
    ld.rounded_rectangle((60 * s, 40 * s, 160 * s, 180 * s), radius=int(16 * s), fill=(200, 210, 225), outline=(150, 160, 180), width=4)
    ld.text((85 * s, 90 * s), "F", fill=(120, 130, 160))
    return L.rotate(ang, expand=True, resample=Image.BICUBIC)

def nose_dot(d, x, y, r=10):
    d.ellipse((x - r, y - r, x + r, y + r), fill=ICING, outline=(230, 190, 60))

def wing_crumbs(d, x, y, h):
    crumbs(d, x - h * 0.33, y - h * 0.42, h / 500); crumbs(d, x + h * 0.33, y - h * 0.42, h / 500)

FLOOR = 1000
B, Mi, Pi = "Mr. Bumble", "Milo", "Pip"
def bumble(x, y=FLOOR, h=760, motion=None, z=0): return Char("bumble_front", x, y, h, who=B, motion=motion, z=z)
def milo(pose, x, y=FLOOR, h=300, motion=None, flip=False, z=0): return Char(pose, x, y, h, flip=flip, who=Mi, motion=motion, z=z)
def pip(pose, x, y=FLOOR, h=360, motion=None, flip=False, z=0): return Char(pose, x, y, h, flip=flip, who=Pi, motion=motion, z=z)

def sill_closeup():
    @functools.lru_cache(None)
    def base():
        im = gradient(W, H, WALL0, WALL1); d = ImageDraw.Draw(im)
        d.rectangle((120, 0, 1800, 640), fill=(255, 255, 252)); d.rectangle((170, 0, 1750, 610), fill=(190, 228, 250))
        d.line((960, 0, 960, 610), fill=(255, 255, 252), width=30)
        d.ellipse((1300, 120, 1560, 380), fill=(255, 244, 190))
        d.rectangle((60, 620, 1860, 720), fill=(255, 255, 255), outline=(215, 225, 235), width=4)
        return im
    return base
# ------------------------------------------------------------------ scene engine
class Char:
    def __init__(self, pose, x, y, h, flip=False, who=None, motion=None, z=0):
        self.pose, self.x, self.y, self.h, self.flip, self.who, self.motion, self.z = pose, x, y, h, flip, who, motion, z

def talking(who, gt):
    return any(l["who"] == who and l["start"] <= gt <= l["end"] for l in LINES)

class Scene:
    def __init__(self, base, chars=(), back=None, front=None, cam=None, wind=0.0, layers=(), post=None):
        self.base, self.chars, self.back, self.front, self.cam, self.wind, self.layers, self.post = base, list(chars), back, front, cam, wind, layers, post

    def frame(self, t, d, gt):
        im = (self.base() if callable(self.base) else self.base).copy()
        dr = ImageDraw.Draw(im, "RGBA")
        wind = self.wind(t, d) if callable(self.wind) else self.wind
        if self.back: self.back(im, dr, t, d, wind)
        for c in sorted(self.chars, key=lambda c: c.z):
            st = dict(dx=0, dy=0, rot=0, sx=1, sy=1, pose=c.pose, flip=c.flip, tint=0, hide=False, h=c.h)
            if c.motion: st.update(c.motion(t, d) or {})
            if st["hide"]: continue
            if c.who and talking(c.who, gt):
                ph = (gt * 4.2) % 1
                st["dy"] -= abs(math.sin(math.pi * ph)) * st["h"] * 0.018
                st["sy"] *= 1 + 0.018 * math.sin(2 * math.pi * ph)
            else:
                st["sy"] *= 1 + 0.008 * math.sin(2 * math.pi * (gt * 0.6 + c.x / 700))
            sp = sprite(st["pose"], int(st["h"]), st["flip"], int(round(st["tint"] * 10)))
            if st["sx"] != 1 or st["sy"] != 1:
                sp = sp.resize((max(1, int(sp.width * st["sx"])), max(1, int(sp.height * st["sy"]))), Image.BILINEAR)
            if st["rot"]: sp = sp.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
            x, y = c.x + st["dx"], c.y + st["dy"]
            if c.y < H + 40 and st["h"] < 700:
                dr.ellipse((x - sp.width * 0.38, c.y - 14, x + sp.width * 0.38, c.y + 14), fill=(120, 70, 40, 60))
            im.paste(sp, (int(x - sp.width / 2), int(y - sp.height)), sp)
        if self.front: self.front(im, dr, t, d, wind)
        for L in self.layers: L(im, ImageDraw.Draw(im, "RGBA"), t, d, wind)
        if self.cam:
            z0, fx0, fy0, z1, fx1, fy1 = self.cam
            e = ease(t / d); z, fx, fy = lerp(z0, z1, e), lerp(fx0, fx1, e), lerp(fy0, fy1, e)
            if abs(z - 1) > 1e-3:
                cw, ch = W / z, H / z
                x0 = min(max(0, fx - cw / 2), W - cw); y0 = min(max(0, fy - ch / 2), H - ch)
                im = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        if self.post: im = self.post(im, t, d)
        return im

def img_layer(fn):
    def f(im, dr, t, d, w):
        L = fn(); im.paste(L, (0, 0), L)
    return f

def layers(*fs):
    def f(im, dr, t, d, wind):
        for g in fs:
            if g: g(im, dr, t, d, wind)
    return f

def cap(text, hi, t0, t1, pos="low"):
    return lambda im, dr, t, d, wind: caption(im, text, hi, t, t0, t1, pos)

def hop(amp, rate, t0=0, t1=99):
    return lambda t, d: dict(dy=-abs(math.sin(math.pi * rate * (t - t0))) * amp) if t0 <= t <= t1 else {}

def shake(amp, rate=18):
    return lambda t, d: dict(dx=amp * math.sin(t * rate))

def comb(*fs):
    def m(t, d):
        o = dict(dx=0, dy=0, rot=0, sx=1, sy=1)
        for f in fs:
            for k, v in (f(t, d) or {}).items():
                if k in ("dx", "dy", "rot"): o[k] += v
                elif k in ("sx", "sy"): o[k] *= v
                else: o[k] = v
        return o
    return m

def const(**kw): return lambda t, d: dict(kw)

def breathing(inhales):
    """inhales: list of (start, peak_time, end) -> body puffs up and settles."""
    def m(t, d):
        s = 0.0
        for a, p, b in inhales:
            if a <= t <= p: s = max(s, ease((t - a) / (p - a)))
            elif p < t <= b: s = max(s, 1 - ease((t - p) / (b - p)))
        return dict(sx=1 + 0.09 * s, sy=1 + 0.07 * s)
    return m

# ------------------------------------------------------------------ shots
def L(fn):  # wrap a drawing function f(dr, t, d) as a scene layer
    return lambda im, dr, t, d, w: fn(dr, t, d)

def tray_on_sill(state="eleven"):
    return L(lambda dr, t, d: tray(dr, 510, 485, 0.75, state))

def tray_on_table(state="eleven", hi=lambda t, d: -1, lop=lambda t, d: 1.0, s=1.0, x=760, y=820):
    return L(lambda dr, t, d: tray(dr, x, y, s, state, hi(t, d), lop(t, d)))

def bumble_face(x, y, h, a=1.0):
    return L(lambda dr, t, d: flour_face(dr, x, y - h * 0.73, h * 0.26, a))

def count_hi(t0, gap, first, n):
    def f(t, d):
        k = int((t - t0) / gap)
        return first + k if 0 <= k < n and t >= t0 else -1
    return f

def build(sid):
    K = kitchen
    sink = lambda t, d: dict(sy=0.92, dy=10, tint=-0.6)
    if sid == "S01":
        def wing(dr, t, d):
            p = ramp(t, 1.0, 2.4) - ramp(t, 2.8, 4.0)
            x = lerp(2050, 1390, p); y = 520
            dr.ellipse((x - 120, y - 70, x + 120, y + 70), fill=(250, 215, 80), outline=(200, 160, 50), width=4)
            if 2.6 < t < 4.0: star(dr, x - 90, y - 10, 70, 10)
        return Scene(sill_closeup(), layers=[L(lambda dr, t, d: tray(dr, 960, 520, 2.6, "twelve" if t < 2.6 else "eleven")), L(wing)], cam=(1.0, 960, 540, 1.05, 1100, 520))
    if sid == "S02":
        def chew(t, d): return dict(sy=1 + 0.04 * math.sin(t * 14), dy=4 * math.sin(t * 14))
        return Scene(K, chars=[milo("milo_happy", 1480, 830, 300, chew)], front=img_layer(counter_front),
                     back=tray_on_sill(), layers=[L(lambda dr, t, d: crumbs(dr, 1480, 640, 1.2))], cam=(1.6, 1440, 640, 1.6, 1440, 640))
    if sid == "S03":
        return Scene(K, chars=[bumble(-120, motion=lambda t, d: dict(dx=lerp(0, 560, ramp(t, 0, 1.6)), dy=-abs(math.sin(t * 7)) * 12 * (t < 1.6), rot=3 * math.sin(t * 7) * (t < 1.6)))],
                     back=tray_on_sill())
    if sid == "S04":
        def gulp(t, d): return dict(sy=1 - 0.08 * (ramp(t, 0.3, 0.5) - ramp(t, 0.5, 0.8)), sx=1 + 0.05 * (ramp(t, 0.3, 0.5) - ramp(t, 0.5, 0.8)))
        return Scene(K, chars=[milo("milo_surprised", 960, 1240, 900, gulp)], layers=[cap("UH-OH!", ["UH-OH!"], 0.6, 2.9, "top")], cam=(1.0, 960, 540, 1.06, 960, 520))
    if sid in ("S05", "S14", "S30", "S41"):
        bm = None
        if sid == "S14": bm = lambda t, d: dict(rot=4 * math.sin(t * 3))
        if sid == "S41": bm = lambda t, d: dict(rot=-3)
        mm = None if sid != "S14" else (lambda t, d: dict(sy=1.03))
        if sid == "S30": mm = None
        trayl = tray_on_sill() if sid == "S05" else tray_on_table()
        cam = {"S05": (1.0, 960, 540, 1.08, 960, 560), "S14": None, "S30": (1.0, 960, 540, 1.1, 1000, 600), "S41": None}[sid]
        mp = "milo_front"
        return Scene(K, chars=[pip("pip_front", 560, 990), milo(mp, 1030, 1010, motion=mm), bumble(1440, 1010, 740, bm)],
                     back=trayl, layers=([bumble_face(1440, 1010, 740, 0.5)] if sid == "S14" else []), cam=cam)
    if sid == "S06":
        return Scene(K, chars=[bumble(880, 1320, 1150, lambda t, d: dict(rot=3 * math.sin(t * 2)))],
                     back=tray_on_sill(), layers=[L(lambda dr, t, d: paper_list(dr, 1330, 760 + 10 * math.sin(t * 3), 1.4))])
    if sid == "S07":
        return Scene(K, chars=[pip("pip_front", 900, 960, 760)], front=img_layer(table_front),
                     layers=[L(lambda dr, t, d: nose_dot(dr, 900, 960 - 760 * 0.6, 14)), L(lambda dr, t, d: icing_bag(dr, 1230, 640 - 30 * ramp(t, 0.4, 1.0), 1.3))])
    if sid in ("S08", "S52"):
        t0 = 1.6 if sid == "S08" else 2.0
        bm = lambda t, d: dict(rot=(-6 * ramp(t, t0 - 0.8, t0 - 0.1) + 6 * ramp(t, t0 - 0.1, t0 + 0.2)) if sid == "S52" else 0, dy=-14 * (ramp(t, t0, t0 + 0.15) - ramp(t, t0 + 0.15, t0 + 0.4)))
        lays = []
        if sid == "S08":
            def tin8(im, dr, t, d, w):
                T_ = flour_tin(dr, 0, 0, -35 * ramp(t, 0.3, 1.2), 1.2); im.paste(T_, (1540, 420), T_)
            lays = [tin8,
                    L(lambda dr, t, d: poof(dr, 1440, 1010 - 740 * 0.73, t, t0, 260)),
                    L(lambda dr, t, d: flour_face(dr, 1440, 1010 - 740 * 0.73, 740 * 0.26, ramp(t, t0, t0 + 0.4)))]
            chars = [pip("pip_happy", 560, 990, motion=hop(16, 2.4, 3.6, 7.5)), milo("milo_front", 1030, 1010, motion=hop(20, 2.6, 3.6, 7.5)), bumble(1440, 1010, 740, bm)]
        else:
            lays = [L(lambda dr, t, d: poof(dr, 900, 600, t, t0, 700)),
                    L(lambda dr, t, d: [dust(dr, x, y, h) for x, y, h in ((560, 990, 360), (900, 1010, 300), (1300, 1010, 740))] if t > t0 + 0.6 else None),
                    L(lambda dr, t, d: tray(dr, 1300, 1010 - 740 * 0.42, 0.9, "full"))]
            chars = [pip("pip_happy", 560, 990, motion=hop(16, 2.4, 3.4, 7)), milo("milo_front", 900, 1010, motion=hop(20, 2.6, 3.4, 7)), bumble(1300, 1010, 740, bm)]
        return Scene(K, chars=chars, layers=lays)
    if sid == "S09":
        def m(t, d):
            if t < 1.8: return dict(dy=-abs(math.sin(t * 7)) * 22)
            return dict(dy=6, sy=0.97, tint=-0.3 * ramp(t, 1.8, 3))
        return Scene(K, chars=[milo("milo_front", 960, 1130, 720, m)], layers=[L(lambda dr, t, d: wing_crumbs(dr, 960, 1130, 720) if t > 1.6 else None)])
    if sid in ("S10", "S49"):
        if sid == "S10":
            bm = lambda t, d: dict(dx=lerp(500, -300, ramp(t, 0, 6.5)), dy=-abs(math.sin(t * 5)) * 10, rot=2 * math.sin(t * 5))
            lay = [L(lambda dr, t, d: tray(dr, 1260 + lerp(500, -300, ramp(t, 0, 6.5)), 1180 - 1150 * 0.42 - abs(math.sin(t * 5)) * 10, 1.0, "eleven")), bumble_face(960, 1180, 1150, 0.4)]
            return Scene(K, chars=[bumble(760, 1180, 1150, bm)], layers=[lay[0]])
        lift = lambda t, d: ramp(t, 0.2, 1.4)
        return Scene(K, chars=[bumble(960, 1250, 1100)], layers=[L(lambda dr, t, d: tray(dr, 1180, lerp(1000, 840, lift(t, d)), 1.4, "full", glow=0.6))])
    if sid in ("S11", "S47"):
        if sid == "S11":
            hi = count_hi(0.4, 0.55, 0, 6)
            return Scene(K, chars=[pip("pip_front", 560, 880, 420), bumble(1300, 900, 820), milo("milo_front", 1780, 960, 300)], front=img_layer(table_front),
                         layers=[tray_on_table("eleven", hi, s=1.7, x=900, y=840)], cam=(1.0, 960, 540, 1.05, 900, 600))
        hi = lambda t, d: 9 if 0.4 <= t < 1.0 else (10 if 1.0 <= t < 1.6 else (11 if t >= 2.9 else -1))
        return Scene(K, chars=[pip("pip_happy", 520, 880, 420, hop(20, 2.4, 3.0, 5)), milo("milo_front", 1460, 900, 320, hop(30, 2.6, 2.9, 5)), bumble(1180, 900, 820)],
                     front=img_layer(table_front),
                     layers=[L(lambda dr, t, d: tray(dr, 900, 840, 1.7, "full", hi(t, d), ramp(t, 0.0, 0.9), 1.0 if t > 2.9 else 0.0))], cam=(1.0, 960, 540, 1.08, 900, 640))
    if sid == "S12":
        hi = count_hi(0.4, 0.55, 6, 5)
        return Scene(K, chars=[bumble(1250, 1380, 1200)], layers=[L(lambda dr, t, d: tray(dr, 640, 860, 2.2, "eleven", hi(t, d)))])
    if sid in ("S13", "S48"):
        st = "eleven" if sid == "S13" else "full"
        def sp(dr, t, d):
            if sid == "S48":
                for k in range(6): sparkle(dr, 960 + 380 * math.cos(k * 1.1 + t), 540 + 260 * math.sin(k * 1.7 + t), 26 * abs(math.sin(t * 2 + k)), 230)
        return Scene(sill_closeup(), layers=[L(lambda dr, t, d: tray(dr, 960, 560, 2.8, st, glow=1.0 if sid == "S48" else 0)), L(sp)],
                     cam=(1.0, 960, 540, 1.25, 1260, 700) if sid == "S13" else (1.0, 960, 540, 1.1, 1100, 620))
    if sid == "S15":
        return Scene(K, chars=[milo("milo_happy", 960, 1180, 860, lambda t, d: dict(rot=8 * math.sin(t * 22) if 1.3 < t < 2.4 else 0))],
                     layers=[L(lambda dr, t, d: crumbs(dr, 960, 960, 2.0))])
    if sid in ("S16",):
        return Scene(K, chars=[pip("pip_front", 640, 1010, 430), bumble(1250, 1010, 820, lambda t, d: dict(rot=6 * ramp(t, 0.3, 1.5)))],
                     layers=[L(lambda dr, t, d: nose_dot(dr, 640, 1010 - 430 * 0.6, 8))], cam=(1.0, 960, 540, 1.12, 800, 600))
    if sid == "S17":
        return Scene(K, chars=[pip("pip_front", 960, 1200, 860, lambda t, d: dict(pose="pip_front" if t < 2.0 else "pip_worried", rot=4 * math.sin(t * 9) if 0.6 < t < 1.6 else 0))],
                     layers=[L(lambda dr, t, d: nose_dot(dr, 960, 1200 - 860 * 0.6, 16) if t < 1.2 else None)])
    if sid == "S18":
        return Scene(K, chars=[bumble(880, 1320, 1150, lambda t, d: dict(sy=0.98, rot=-2))], layers=[L(lambda dr, t, d: paper_list(dr, 1330, 800, 1.4))])
    if sid in ("S19", "S38"):
        if sid == "S19": m = lambda t, d: dict(sy=1 - 0.09 * ramp(t, 0.4, 3), dy=30 * ramp(t, 0.4, 3), tint=-0.8 * ramp(t, 0.4, 3))
        else: m = lambda t, d: dict(sy=0.91 + 0.12 * ramp(t, 0.4, 2.5) - 0.03 * ramp(t, 2.5, 3.5), dy=30 - 70 * ramp(t, 0.4, 2.5) + 40 * ramp(t, 2.5, 3.5), tint=-0.6 * (1 - ramp(t, 0.4, 2.5)))
        return Scene(K, chars=[milo("milo_front", 960, 1130, 720, m)], cam=(1.0, 960, 540, 1.06, 960, 520) if sid == "S19" else None)
    if sid == "S20":
        return Scene(K, chars=[pip("pip_worried", 760, 870, 400), milo("milo_worried", 1500, 840, 260, lambda t, d: dict(tint=-0.6))],
                     front=lambda im, dr, t, d, w: (im.paste(table_front(), (0, 0), table_front()), im.paste(counter_front(), (0, 0), counter_front())),
                     back=tray_on_table(s=1.0, x=760, y=830), cam=(1.0, 960, 540, 1.06, 960, 560))
    if sid in ("S21", "S24", "S29"):
        lays = []
        if sid == "S24": lays.append(cap("GUILT", ["GUILT"], 2.6, 5.4, "top"))
        if sid == "S29": lays.append(L(lambda dr, t, d: (crumbs(dr, 700, 1010, 2.2), crumbs(dr, 1220, 1010, 2.2))))
        cam = (1.0, 960, 540, 1.08, 960, 500) if sid == "S24" else None
        return Scene(K, chars=[milo("milo_worried", 960, 1260, 900, lambda t, d: dict(tint=-0.7, rot=2 * math.sin(t * 1.5)))],
                     front=img_layer(counter_front) if sid == "S21" else None, layers=lays, cam=cam)
    if sid == "S22":
        def tin(im, dr, t, d, w):
            a = -150 * ramp(t, 0.6, 2.4)
            T_ = flour_tin(dr, 0, 0, a, 1.6); im.paste(T_, (1180, 380), T_)
            poof(dr, 1300, 640, t, 3.2, 90)
        return Scene(K, chars=[bumble(760, 1320, 1150)], layers=[tin])
    if sid == "S23":
        return Scene(K, chars=[pip("pip_worried", 1150, 1200, 860)], layers=[L(lambda dr, t, d: tray(dr, 480, 900, 1.6, "eleven"))])
    if sid in ("S25", "S26", "S27", "S40"):
        sit = lambda t, d: dict(sy=0.84, dy=110)
        if sid == "S25": sit = lambda t, d: dict(sy=1 - 0.16 * ramp(t, 0.3, 1.6), dy=110 * ramp(t, 0.3, 1.6))
        if sid == "S27": sit = lambda t, d: dict(sy=0.84, dy=110, rot=5 * math.sin(t * 1.5))
        if sid == "S40": sit = lambda t, d: dict(sy=1 - 0.18 * ramp(t, 0.2, 1.4), dy=130 * ramp(t, 0.2, 1.4), rot=6 * ramp(t, 1.2, 2.0))
        mm = (lambda t, d: dict(tint=-0.6, sy=0.95)) if sid != "S40" else None
        cam = {"S26": (1.0, 960, 540, 1.1, 960, 580), "S25": None, "S27": None, "S40": None}[sid]
        return Scene(K, chars=[milo("milo_front", 760, 1040, 380, mm), bumble(1220, 1040, 820, sit)], cam=cam)
    if sid == "S28":
        return Scene(K, chars=[bumble(960, 1500, 1500, lambda t, d: dict(sy=1 + 0.03 * ramp(t, 0, 3)))], cam=(1.0, 960, 540, 1.06, 960, 480))
    if sid in ("S31", "S34", "S35", "S39", "S53"):
        mm = lambda t, d: dict(tint=-0.4)
        lays = []
        if sid == "S31": lays.append(L(lambda dr, t, d: thought(dr, 1240, 300, t, 0.4)))
        if sid == "S34":
            mm = lambda t, d: dict(tint=-0.4 * (1 - ramp(t, 3, 6)))
            lays += [L(lambda dr, t, d: wing_crumbs(dr, 960, 1130, 720)), cap("TELLING THE TRUTH", ["TRUTH"], 0.5, 3.8, "top")]
        if sid == "S35": mm = lambda t, d: dict(tint=-0.2, dy=20 * (ramp(t, 0.5, 1.5) - ramp(t, 3, 4)))
        if sid == "S39":
            mm = hop(40, 2.4)
            lays.append(L(lambda dr, t, d: [sparkle(dr, 960 + 380 * math.cos(k * 1.4 + t), 520 + 300 * math.sin(k * 1.9 + t), 24 * abs(math.sin(t * 3 + k)), 230) for k in range(6)]))
        if sid == "S53":
            mm = None; lays.append(L(lambda dr, t, d: dust(dr, 960, 1130, 720)))
        return Scene(K, chars=[milo("milo_front", 960, 1130, 720, mm)], layers=lays, cam=(1.0, 960, 540, 1.08, 960, 520) if sid in ("S34", "S53") else None)
    if sid == "S32":
        def m(t, d):
            if t < 1.5: return dict(pose="milo_front", sx=1 + 0.08 * (ramp(t, 0.6, 1.2) - ramp(t, 1.2, 1.5)), tint=-0.3)
            if t < 5.0: return dict(pose="milo_side", flip=True, dx=-560 * ramp(t, 1.6, 5.0), dy=-abs(math.sin(t * 6)) * 12)
            return dict(pose="milo_front", dx=-560)
        return Scene(K, chars=[milo("milo_front", 1520, 1020, 380, m)], back=tray_on_sill())
    if sid == "S33":
        return Scene(K, chars=[pip("pip_front", 560, 990, motion=lambda t, d: dict(rot=-5 * ramp(t, 2, 3))), milo("milo_front", 960, 1050, 380),
                               bumble(1420, 1010, 740, lambda t, d: dict(rot=5 * ramp(t, 2, 3)))])
    if sid == "S36":
        return Scene(K, chars=[pip("pip_worried", 700, 1040, 460), milo("milo_side", 1150, 1040, 380, flip=True)], cam=(1.0, 960, 540, 1.06, 940, 600))
    if sid == "S37":
        return Scene(K, chars=[pip("pip_worried", 960, 1200, 860, lambda t, d: dict(pose="pip_worried" if t < 2.4 else "pip_happy", dy=-20 * (ramp(t, 2.4, 2.7) - ramp(t, 2.7, 3.1))))])
    if sid == "S42":
        return Scene(K, chars=[pip("pip_happy", 960, 1200, 860, lambda t, d: dict(dy=-30 * (ramp(t, 0.2, 0.5) - ramp(t, 0.5, 0.9)), dx=-1300 * ramp(t, 3.2, 6.5)))])
    if sid == "S43":
        def bag(dr, t, d):
            x = lerp(-120, 600, ramp(t, 0, 1.6)) + 90
            dr.rounded_rectangle((x - 50, 760, x + 50, 880), radius=20, fill=(250, 248, 240), outline=(200, 190, 175), width=4)
        return Scene(K, chars=[pip("pip_happy", -120, 990, motion=lambda t, d: dict(dx=lerp(0, 720, ramp(t, 0, 1.6)), dy=-abs(math.sin(t * 6)) * 30 * (t < 1.6))),
                               milo("milo_front", 1040, 1010, motion=hop(30, 2.6, 1.8, 4)), bumble(1440, 1010, 740, hop(16, 2, 2, 4))], layers=[L(bag)])
    if sid == "S44":
        def bake(dr, t, d):
            # bowl + spoon (Milo), rolling pin (Mr. Bumble), star cutter result (Pip)
            dr.chord((780, 700, 1000, 860), 0, 180, fill=(240, 150, 120)); dr.ellipse((780, 750, 1000, 800), fill=(250, 235, 200))
            a = t * 2.5; dr.line((890, 770, 890 + 70 * math.cos(a), 700 + 20 * math.sin(a)), fill=(170, 120, 70), width=12)
            px = 1300 + 60 * math.sin(t * 3)
            dr.ellipse((1150, 760, 1450, 810), fill=(245, 225, 185)); dr.rounded_rectangle((px - 110, 740, px + 110, 770), radius=14, fill=(200, 150, 100))
            if t > 4.5: star(dr, 600, 780, 46, 0, False)
            if t > 6.0: star(dr, 1000, 900, 46, 12, True)
        return Scene(K, chars=[pip("pip_front", 560, 900, 400), milo("milo_front", 890, 900, 330, lambda t, d: dict(rot=3 * math.sin(t * 5))), bumble(1300, 900, 760)],
                     front=img_layer(table_front), layers=[L(bake)], cam=(1.0, 960, 540, 1.06, 1000, 600))
    if sid == "S45":
        def oven(dr, t, d):
            if t > 1.2:
                dr.ellipse((1640, 610, 1800, 770), fill=(255, 190, 110))
            if t > 1.8:
                star(dr, 1180, 600, 70, 12, True, glow=0.8)
        return Scene(K, chars=[bumble(1260, 1010, 820, lambda t, d: dict(rot=-6 * ramp(t, 0.8, 1.6) + 6 * ramp(t, 1.8, 2.6)))], layers=[L(oven)])
    if sid == "S46":
        def lay(dr, t, d):
            star(dr, 900, 840, 60, 12, True)
            icing_bag(dr, 1060, 760, 0.8)
            if t > 1.6: nose_dot(dr, 1180, 880 - 380 * 0.69, 12)
        return Scene(K, chars=[pip("pip_happy", 640, 880, 430, hop(10, 2.5, 3.4, 6.5)), milo("milo_front", 1180, 880, 380, hop(10, 2.4, 3.6, 6.5))],
                     front=img_layer(table_front), layers=[L(lay)])
    if sid == "S50":
        return Scene(K, chars=[pip("pip_happy", 760, 1040, 460, lambda t, d: dict(dx=110 * ramp(t, 0.4, 1.4))), milo("milo_side", 1180, 1040, 380, lambda t, d: dict(dx=-120 * ramp(t, 0.4, 1.4)), flip=True, z=1)])
    if sid == "S51":
        walk = lambda off, sp: (lambda t, d: dict(dx=-sp * ramp(t, 0.3, 6.8), dy=-abs(math.sin(t * 6 + off)) * 16))
        return Scene(K, chars=[bumble(1300, 1010, 740, lambda t, d: dict(dx=-1000 * ramp(t, 0.3, 6.8), rot=2 * math.sin(t * 5))),
                               milo("milo_side", 1600, 1020, 320, walk(0, 1150), flip=True), pip("pip_side", 1780, 1010, 380, walk(1, 1150), flip=True)],
                     layers=[L(lambda dr, t, d: tray(dr, 1300 - 1000 * ramp(t, 0.3, 6.8), 1010 - 740 * 0.42, 0.9, "full"))])
    if sid == "S54":
        sc = Scene(K, chars=[pip("pip_happy", 560, 990, motion=lambda t, d: dict(rot=6 * math.sin(t * 4))), milo("milo_front", 900, 1010, motion=lambda t, d: dict(rot=6 * math.sin(t * 4 + 1))),
                             bumble(1300, 1010, 740, lambda t, d: dict(rot=3 * math.sin(t * 3)))],
                   layers=[L(lambda dr, t, d: tray(dr, 1300, 1010 - 740 * 0.42, 0.9, "full")),
                           L(lambda dr, t, d: [dust(dr, x, y, h) for x, y, h in ((560, 990, 360), (900, 1010, 300), (1300, 1010, 740))]),
                           cap("THE TRUTH FEELS LIGHTER", ["LIGHTER"], 0.8, 6.0, "mid")], cam=(1.12, 960, 600, 1.0, 960, 540))
        sc.post = lambda im, t, d: Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), ramp(t, 5.0, 6.0))
        return sc
    raise ValueError(sid)

# ------------------------------------------------------------------ render
def render_shot(sid):
    s = SH[sid]; d = s["dur"]; n = d * FPS
    path = os.path.join(SEG, sid + ".mp4")
    if os.path.exists(path) and os.environ.get("REUSE"): return path
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    sc = build(sid)
    for i in range(n):
        p.stdin.write(sc.frame(i / FPS, d, s["start"] + i / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    return path

def main():
    only = sys.argv[1:]
    with Pool(4) as pool:
        for pth in pool.imap_unordered(render_shot, only or [s["id"] for s in plan.SHOTS]):
            print("done", os.path.basename(pth), flush=True)
    if only: return
    lst = os.path.join(SEG, "list.txt")
    with open(lst, "w") as f:
        for s in plan.SHOTS: f.write(f"file '{os.path.join(SEG, s['id'] + '.mp4')}'\n")
    final = os.path.join(HERE, "..", "ep3_milo_and_the_missing_cookie.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", "360", "-movflags", "+faststart", final], check=True)
    print("final", final)

if __name__ == "__main__":
    main()
