"""Render Episode 1 (6:00, 1920x1080, 24 fps) from the character cutouts, with the soundtrack from audio.py.

Each shot of the timeline is built from simple drawn sets (garden, tulips, pond, sunflowers, fence end, sky,
clue cards) and the character poses cut from the reference sheets. Characters bob while their line plays.
Usage: python3 cutouts.py && python3 audio.py && python3 render.py   -> ../ep1_milo_and_the_missing_rainbow_color.mp4
"""
import os, sys, json, math, csv, subprocess, functools
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SEG = os.path.join(OUT, "segments"); os.makedirs(SEG, exist_ok=True)
W, H, FPS = 1920, 1080, 24
FONT = os.path.join(HERE, "fonts", "Fredoka.ttf")

shots = list(csv.DictReader(open(os.path.join(HERE, "..", "shots.csv"))))
for s in shots:
    s["start"], s["end"] = int(s["start"]), int(s["end"])
SH = {s["shot"]: s for s in shots}
LINES = json.load(open(os.path.join(OUT, "lines.json")))

# ------------------------------------------------------------------ palette
SKY_TOP, SKY_LOW = (132, 196, 240), (214, 238, 252)
GRASS_TOP, GRASS_LOW = (150, 214, 120), (104, 178, 92)
RAIN = [(250, 120, 125), (255, 178, 105), (255, 226, 110), (130, 210, 125), (95, 160, 245), (175, 135, 225)]
BLUE = RAIN[4]

def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)

def lerp(a, b, x):
    return a + (b - a) * x

# ------------------------------------------------------------------ sprites
@functools.lru_cache(None)
def sprite(pose, h, flip=False):
    im = Image.open(os.path.join(HERE, "cutouts", pose + ".png")).convert("RGBA")
    w = max(1, round(im.width * h / im.height))
    im = im.resize((w, int(h)), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im

def shadow(d, x, y, w):
    d.ellipse((x - w / 2, y - w * 0.09, x + w / 2, y + w * 0.09), fill=(70, 130, 70, 70))

# ------------------------------------------------------------------ drawing helpers (draw at scale k)
def gradient(w, h, top, low, y0=0, y1=None):
    y1 = y1 or h
    a = np.zeros((h, w, 3), np.uint8)
    t = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None]
    for c in range(3):
        a[:, :, c] = (top[c] + (low[c] - top[c]) * t).astype(np.uint8)
    return Image.fromarray(a, "RGB").convert("RGBA")

def cloud(d, x, y, s):
    for dx, dy, r in [(-1.0, 0.15, 0.55), (-0.35, -0.25, 0.75), (0.45, -0.1, 0.65), (1.0, 0.2, 0.5), (0, 0.25, 0.7)]:
        d.ellipse((x + (dx - r) * s, y + (dy - r) * s, x + (dx + r) * s, y + (dy + r) * s), fill=(255, 255, 255, 245))

def rainbow_layer(w, h, cx, cy, r, band, blue=0.0, alpha=215):
    """blue: 0 = gap, 1 = complete, between = blue band filling from the left."""
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for i, col in enumerate(RAIN):
        ro = r - i * band
        box = (cx - ro, cy - ro, cx + ro, cy + ro)
        if i == 4:
            if blue > 0:
                d.arc(box, 180, 180 + 180 * blue, fill=col + (alpha,), width=int(band) + 1)
            continue
        d.arc(box, 180, 360, fill=col + (alpha,), width=int(band) + 1)
    return L

def tulip(d, x, y, s, rot=0.0, col=(235, 70, 85)):
    top = (x + rot * 30 * s, y - 120 * s)
    d.line((x, y, top[0], top[1] + 20 * s), fill=(80, 160, 70), width=max(2, int(8 * s)))
    d.ellipse((x - 34 * s, y - 70 * s, x + 4 * s, y - 20 * s), fill=(95, 180, 80))
    cx, cy = top
    d.ellipse((cx - 30 * s, cy - 10 * s, cx + 30 * s, cy + 40 * s), fill=col)
    for k in (-1, 0, 1):
        d.polygon([(cx + k * 20 * s - 14 * s, cy + 10 * s), (cx + k * 20 * s, cy - 30 * s), (cx + k * 20 * s + 14 * s, cy + 10 * s)], fill=col)
    d.ellipse((cx - 12 * s, cy, cx - 2 * s, cy + 14 * s), fill=(255, 160, 170))

def sunflower(d, x, y, s, height=600):
    hy = y - height * s
    d.line((x, y, x, hy), fill=(90, 160, 70), width=max(3, int(14 * s)))
    for k, yy in enumerate(np.linspace(y - 120 * s, hy + 140 * s, 3)):
        sd = -1 if k % 2 else 1
        d.ellipse((x + (10 if sd > 0 else -110) * s, yy - 30 * s, x + (110 if sd > 0 else -10) * s, yy + 30 * s), fill=(100, 180, 80))
    R = 95 * s
    for a in range(0, 360, 24):
        ax, ay = x + math.cos(math.radians(a)) * R * 0.85, hy + math.sin(math.radians(a)) * R * 0.85
        d.ellipse((ax - 38 * s, ay - 38 * s, ax + 38 * s, ay + 38 * s), fill=(255, 205, 50))
    d.ellipse((x - 52 * s, hy - 52 * s, x + 52 * s, hy + 52 * s), fill=(140, 90, 50))

def fence(d, x0, x1, ybase, hgt, step, persp=None):
    xs = np.arange(x0, x1, step)
    d.rectangle((x0, ybase - hgt * 0.75, x1, ybase - hgt * 0.62), fill=(250, 250, 248))
    d.rectangle((x0, ybase - hgt * 0.35, x1, ybase - hgt * 0.22), fill=(250, 250, 248))
    for x in xs:
        w = step * 0.55
        d.polygon([(x, ybase), (x, ybase - hgt * 0.88), (x + w / 2, ybase - hgt), (x + w, ybase - hgt * 0.88), (x + w, ybase)], fill=(255, 255, 255), outline=(215, 215, 215))

def lilypad(d, x, y, r):
    d.ellipse((x - r, y - r * 0.38, x + r, y + r * 0.38), fill=(90, 175, 85))
    d.pieslice((x - r, y - r * 0.38, x + r, y + r * 0.38), 300, 330, fill=(120, 190, 230))
    d.ellipse((x - r * 0.75, y - r * 0.25, x + r * 0.55, y + r * 0.2), outline=(120, 200, 105), width=3)

def pinwheel(d, x, y, r, ang, glow=0.0):
    if glow > 0:
        for k in range(6, 0, -1):
            rr = r * (1 + 0.25 * k * glow)
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(140, 195, 255, int(16 * glow)))
    for i in range(4):
        a = math.radians(ang + i * 90)
        p0 = (x, y)
        p1 = (x + math.cos(a) * r, y + math.sin(a) * r)
        p2 = (x + math.cos(a + math.radians(70)) * r * 0.75, y + math.sin(a + math.radians(70)) * r * 0.75)
        d.polygon([p0, p1, p2], fill=(70, 140, 240) if i % 2 else (120, 180, 255))
        d.line([p0, p1], fill=(255, 255, 255), width=max(1, int(r * 0.03)))
    d.ellipse((x - r * 0.1, y - r * 0.1, x + r * 0.1, y + r * 0.1), fill=(255, 220, 80))

def pot_and_stick(d, x, y, s):
    d.line((x, y - 20 * s, x, y - 260 * s), fill=(150, 110, 70), width=max(2, int(8 * s)))
    d.polygon([(x - 60 * s, y - 70 * s), (x + 60 * s, y - 70 * s), (x + 45 * s, y + 30 * s), (x - 45 * s, y + 30 * s)], fill=(215, 120, 80))
    d.rectangle((x - 68 * s, y - 85 * s, x + 68 * s, y - 62 * s), fill=(230, 140, 95))

def sparkle(d, x, y, r, a=255, col=(255, 255, 255)):
    d.polygon([(x, y - r), (x + r * 0.22, y - r * 0.22), (x + r, y), (x + r * 0.22, y + r * 0.22), (x, y + r),
               (x - r * 0.22, y + r * 0.22), (x - r, y), (x - r * 0.22, y - r * 0.22)], fill=col + (a,))

# ------------------------------------------------------------------ sets (static backgrounds, cached)
@functools.lru_cache(None)
def set_image(name, rain="gap", wide=1):
    k = 2  # supersample
    w, h = W * wide * k, H * k
    im = gradient(w, h, SKY_TOP, SKY_LOW, 0, int(h * 0.62))
    rb = 0.0 if rain == "gap" else 1.0
    if rain != "none":
        im.alpha_composite(rainbow_layer(w, h, (W * wide / 2) * k, 720 * k, 760 * k, 44 * k, rb))
    d = ImageDraw.Draw(im)
    rs = np.random.default_rng(len(name) * 7 + wide)
    for c in range(wide):
        for (x, y, s) in [(260, 170, 70), (1580, 130, 85), (1240, 300, 50), (520, 360, 45)]:
            cloud(d, (c * W + x + rs.uniform(-60, 60)) * k, y * k, s * k)
    horizon = 640
    if name in ("garden", "tulips", "sunflowers", "fenceend", "pond", "path"):
        d.ellipse((-400 * k, (horizon - 90) * k, w * 0.6, (horizon + 400) * k), fill=(160, 220, 128))
        d.ellipse((w * 0.4, (horizon - 60) * k, w + 400 * k, (horizon + 400) * k), fill=(150, 214, 120))
        g = gradient(w, h - horizon * k, GRASS_TOP, GRASS_LOW)
        im.paste(g, (0, horizon * k))
        d = ImageDraw.Draw(im)
        for _ in range(140 * wide):  # grass tufts
            x, y = rs.uniform(0, w), rs.uniform((horizon + 20) * k, h)
            d.line((x, y, x + rs.uniform(-6, 6) * k, y - rs.uniform(8, 20) * k), fill=(90, 165, 80), width=2 * k)
        for _ in range(26 * wide):  # little flowers
            x, y = rs.uniform(0, w), rs.uniform((horizon + 40) * k, h)
            c = [(255, 255, 255), (255, 210, 230), (255, 240, 150)][rs.integers(3)]
            d.ellipse((x - 5 * k, y - 5 * k, x + 5 * k, y + 5 * k), fill=c)
    if name in ("garden", "path", "sunflowers", "fenceend"):
        fence(d, 0, w, (horizon + 40) * k, 120 * k, 70 * k)
    if name in ("garden", "path"):
        for c in range(wide):
            for (x, y, rx) in [(300, 900, 150), (1500, 860, 120), (1100, 1010, 170)]:
                d.ellipse(((c * W + x - rx) * k, (y - rx * 0.22) * k, (c * W + x + rx) * k, (y + rx * 0.22) * k), fill=(170, 210, 240))
                d.ellipse(((c * W + x - rx * 0.6) * k, (y - rx * 0.12) * k, (c * W + x - rx * 0.1) * k, (y - rx * 0.02) * k), fill=(225, 242, 252))
    if name == "path":
        for i in range(int(14 * wide)):
            x = (i * 260 + 80) * k; y = (900 + 40 * math.sin(i * 0.9)) * k
            d.ellipse((x - 90 * k, y - 28 * k, x + 90 * k, y + 28 * k), fill=(205, 200, 190), outline=(180, 175, 165), width=3 * k)
    if name == "tulips":
        for i in range(16):
            tulip(d, (60 + i * 120 + rs.uniform(-20, 20)) * k, (700 + rs.uniform(-10, 10)) * k, 0.9 * k)
    if name == "pond":
        d.ellipse((140 * k, 700 * k, 1780 * k, 1150 * k), fill=(110, 175, 220))
        d.ellipse((240 * k, 730 * k, 1680 * k, 1100 * k), fill=(130, 190, 232))
        for i in range(6):
            x = rs.uniform(300, 1600); y = rs.uniform(780, 1000)
            d.arc(((x - 80) * k, (y - 12) * k, (x + 80) * k, (y + 12) * k), 200, 340, fill=(200, 230, 250), width=3 * k)
    if name == "sunflowers":
        for i, x in enumerate([180, 420, 1500, 1760, 640, 1290]):
            sunflower(d, x * k, (700 + (i % 2) * 20) * k, (1.0 if i < 4 else 0.85) * k, height=560 + (i % 3) * 40)
    if name == "fenceend":
        d.rectangle((1180 * k, 470 * k, 1260 * k, 690 * k), fill=(255, 255, 255), outline=(215, 215, 215), width=3 * k)
        d.rectangle((1260 * k, 0, w, h), fill=(0, 0, 0, 0))  # end of fence
        im2 = gradient(w, h, SKY_TOP, SKY_LOW, 0, int(h * 0.62))
        ImageDraw.Draw(im2)
        # rebuild right side: sky + grass past the fence end (keep rainbow)
        if rain != "none":
            im2.alpha_composite(rainbow_layer(w, h, 960 * k, 720 * k, 760 * k, 44 * k, rb))
        crop = im2.crop((1262 * k, 0, w, horizon * k)); im.paste(crop, (1262 * k, 0))
        g = gradient(w - 1262 * k, h - horizon * k, GRASS_TOP, GRASS_LOW); im.paste(g, (1262 * k, horizon * k))
        d = ImageDraw.Draw(im)
        cloud(d, 1600 * k, 180 * k, 70 * k)
        d.ellipse((1120 * k, 455 * k, 1320 * k, 490 * k), fill=(255, 255, 255))
        pot_and_stick(d, 1220 * k, 455 * k, 1.0 * k)
    return im.resize((W * wide, H), Image.LANCZOS)

@functools.lru_cache(None)
def front_layer(name):
    L = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    rs = np.random.default_rng(3)
    if name == "tulips":
        for i in range(11):
            tulip(d, (30 + i * 190 + rs.uniform(-30, 30)) * 2, (1140 + rs.uniform(-20, 30)) * 2, 1.9 * 2)
    if name == "pondfront":
        for x, y, r in [(260, 1040, 160), (1700, 1060, 150)]:
            lilypad(d, x * 2, y * 2, r * 2)
    return L.resize((W, H), Image.LANCZOS)

def card_image(kind, size=760):
    k = 2; s = size * k
    C = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(C)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=90 * k, fill=(255, 253, 246), outline=(235, 225, 205), width=8 * k)
    m = s / 760
    if kind == "tulips":
        for i, x in enumerate([240, 380, 520]):
            tulip(d, x * m, (560 - (i == 1) * 30) * m, 2.2 * m)
    elif kind == "pond":
        d.ellipse((110 * m, 330 * m, 650 * m, 600 * m), fill=(120, 165, 200))
        for x, y, r in [(250, 430, 80), (480, 410, 70), (380, 520, 90)]:
            lilypad(d, x * m, y * m, r * m)
    elif kind == "sunflowers":
        sunflower(d, 270 * m, 650 * m, 0.9 * m, height=480); sunflower(d, 500 * m, 660 * m, 0.9 * m, height=420)
    elif kind == "pinwheel":
        d.line((380 * m, 380 * m, 380 * m, 660 * m), fill=(150, 110, 70), width=int(14 * m))
        pinwheel(d, 380 * m, 330 * m, 190 * m, 20)
    return C.resize((size, size), Image.LANCZOS)

# ------------------------------------------------------------------ scene description
class Char:
    def __init__(self, pose, x, y, h, flip=False, who=None, motion=None, z=0):
        self.pose, self.x, self.y, self.h, self.flip, self.who, self.motion, self.z = pose, x, y, h, flip, who, motion, z

def talking(who, gt):
    for l in LINES:
        if l["who"] == who and l["start"] <= gt <= l["end"]:
            return True
    return False

class Scene:
    def __init__(self, set_name=None, rain="gap", wide=1, chars=(), cam=None, front=None, dyn=None, base=None, post=None, shadows=True):
        self.set_name, self.rain, self.wide = set_name, rain, wide
        self.chars, self.cam, self.front, self.dyn, self.base, self.post, self.shadows = list(chars), cam, front, dyn, base, post, shadows

    def frame(self, t, d, gt):
        if self.base is not None:
            im = self.base(t, d)
        else:
            im = set_image(self.set_name, self.rain, self.wide)
        im = im.convert("RGB")
        dr = ImageDraw.Draw(im, "RGBA")
        if self.dyn:
            self.dyn(im, dr, t, d, "back")
        for c in sorted(self.chars, key=lambda c: c.z):
            st = dict(dx=0, dy=0, rot=0, sx=1, sy=1, pose=c.pose, flip=c.flip, alpha=1, hide=False, scale=1)
            if c.motion:
                st.update(c.motion(t, d) or {})
            if st["hide"]:
                continue
            if c.who and talking(c.who, gt):
                ph = (gt * 4.2) % 1
                st["dy"] -= abs(math.sin(math.pi * ph)) * c.h * 0.02
                st["sy"] *= 1 + 0.02 * math.sin(2 * math.pi * ph)
            else:
                st["sy"] *= 1 + 0.008 * math.sin(2 * math.pi * (gt * 0.6 + c.x / 700))  # breathing
            hh = int(c.h * st["scale"])
            sp = sprite(st["pose"], hh, st["flip"])
            if st["sx"] != 1 or st["sy"] != 1:
                sp = sp.resize((max(1, int(sp.width * st["sx"])), max(1, int(sp.height * st["sy"]))), Image.BILINEAR)
            if st["rot"]:
                sp = sp.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
            x = c.x + st["dx"]; y = c.y + st["dy"]
            if self.shadows and c.h > 150:
                shadow(dr, c.x + st["dx"], c.y + 4, sp.width * 0.8)
            im.paste(sp, (int(x - sp.width / 2), int(y - sp.height)), sp)
        if self.front:
            fl = front_layer(self.front); im.paste(fl, (0, 0), fl)
        if self.dyn:
            self.dyn(im, ImageDraw.Draw(im, "RGBA"), t, d, "front")
        if self.cam:
            z0, fx0, fy0, z1, fx1, fy1 = self.cam
            e = ease(t / d)
            z, fx, fy = lerp(z0, z1, e), lerp(fx0, fx1, e), lerp(fy0, fy1, e)
            cw, ch = W / z, H / z
            x0 = min(max(0, fx - cw / 2), im.width - cw); y0 = min(max(0, fy - ch / 2), im.height - ch)
            if abs(z - 1) < 1e-3 and im.width == W:
                pass
            else:
                im = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        elif im.width != W:
            im = im.crop((0, 0, W, H))
        if self.post:
            im = self.post(im, t, d)
        return im

# ------------------------------------------------------------------ motions
def hop(amp=40, rate=1.6, t0=0, t1=99):
    def m(t, d):
        if t0 <= t <= t1:
            return dict(dy=-abs(math.sin(math.pi * rate * (t - t0))) * amp)
        return {}
    return m

def walk(x0, x1, amp=40, rate=1.8, pose=None):
    def m(t, d):
        return dict(dx=lerp(x0, x1, t / d), dy=-abs(math.sin(math.pi * rate * t)) * amp)
    return m

def wave(amp=6, rate=1.5):
    return lambda t, d: dict(rot=amp * math.sin(2 * math.pi * rate * t))

def seq(*parts):
    """parts: (t_from, motion_fn_or_dict)"""
    def m(t, d):
        cur = {}
        for tf, f in parts:
            if t >= tf:
                cur = f(t - tf, d) if callable(f) else dict(f)
        return cur
    return m

def combine(*fs):
    def m(t, d):
        out = dict(dx=0, dy=0, rot=0, sx=1, sy=1)
        for f in fs:
            r = f(t, d) or {}
            for k, v in r.items():
                if k in ("dx", "dy", "rot"): out[k] += v
                elif k in ("sx", "sy"): out[k] *= v
                else: out[k] = v
        return out
    return m

def card_glow(x, y, sc=1.0, until=99):
    def dyn(im, dr, t, d, layer):
        if layer != "back" or t > until: return
        g = 0.6 + 0.4 * math.sin(t * 4)
        for k in range(5, 0, -1):
            r = 34 * sc * (1 + 0.3 * k)
            dr.ellipse((x - r * 1.3, y - r * 0.6, x + r * 1.3, y + r * 0.6), fill=(255, 250, 200, int(20 * g)))
        dr.rounded_rectangle((x - 40 * sc, y - 28 * sc, x + 40 * sc, y + 28 * sc), radius=10 * sc, fill=(255, 253, 246), outline=(230, 220, 200), width=2)
        tulip(dr, x - 8 * sc, y + 18 * sc, 0.28 * sc)
        tulip(dr, x + 12 * sc, y + 18 * sc, 0.25 * sc)
        sparkle(dr, x + 34 * sc, y - 30 * sc, 12 * sc * g)
    return dyn

def multi(*dyns):
    def dyn(im, dr, t, d, layer):
        for f in dyns:
            if f: f(im, dr, t, d, layer)
    return dyn

def sparkles_dyn(cx, cy, spread, n=10, layer_name="front", col=(255, 255, 255)):
    rs = np.random.default_rng(int(cx + cy))
    pts = [(rs.uniform(-spread, spread), rs.uniform(-spread * 0.5, spread * 0.5), rs.uniform(0, 6), rs.uniform(8, 22)) for _ in range(n)]
    def dyn(im, dr, t, d, layer):
        if layer != layer_name: return
        for (dx, dy, ph, r) in pts:
            a = max(0, math.sin(t * 2.5 + ph))
            sparkle(dr, cx + dx, cy + dy, r * a, int(230 * a), col)
    return dyn

def pinwheel_dyn(x, y, r, speed_fn, glow_fn=lambda t, d: 0.0):
    state = {}
    def dyn(im, dr, t, d, layer):
        if layer != "front": return
        ang = speed_fn(t, d)
        pinwheel(dr, x, y, r, ang, glow_fn(t, d))
    return dyn

def dot(col):
    def post(im, t, d):
        dr = ImageDraw.Draw(im)
        a = ease(t / 0.5)
        r = 70 * a
        dr.ellipse((1760 - r - 8, 150 - r - 8, 1760 + r + 8, 150 + r + 8), fill=(255, 255, 255))
        dr.ellipse((1760 - r, 150 - r, 1760 + r, 150 + r), fill=col)
        return im
    return post

# ------------------------------------------------------------------ the shots
GROUND = 1000

def card_shot(kind, holder):
    bgcol = {"tulips": (160, 210, 140), "pond": (150, 200, 210), "sunflowers": (190, 215, 140), "pinwheel": (190, 220, 160)}[kind]
    @functools.lru_cache(None)
    def base_img():
        bg = set_image({"tulips": "tulips", "pond": "pond", "sunflowers": "sunflowers", "pinwheel": "sunflowers"}[kind]).filter(ImageFilter.GaussianBlur(28))
        card = card_image(kind)
        bg.alpha_composite(card, ((W - card.width) // 2, (H - card.height) // 2 + 20))
        d = ImageDraw.Draw(bg)
        col = (250, 215, 80) if holder == "milo" else (190, 170, 230)
        for sx in (-1, 1):  # wings / paws holding the card edges
            cx = W / 2 + sx * 395; cy = H / 2 + 230
            d.ellipse((cx - 70, cy - 110, cx + 70, cy + 110), fill=col)
        return bg
    def dyn(im, dr, t, d, layer):
        if layer != "front": return
        p = (t - 0.4) / 1.6
        if 0 <= p <= 1:
            x = W / 2 - 380 + 760 * p
            for k in range(4):
                sparkle(dr, x - k * 40, H / 2 - 300 + k * 160 + 60 * math.sin(p * 6 + k), 26 - k * 3, 230)
    return Scene(base=lambda t, d: base_img(), dyn=dyn, cam=(1.0, W / 2, H / 2, 1.06, W / 2, H / 2))

def build(shot):
    M, P = "Milo", "Pip"
    if shot == "S01":
        return Scene("garden", chars=[Char("milo_front", 700, 930, 300, who=M, motion=seq((0, hop(60, 1.2, 0, 0.8)), (0.85, {}), (3.0, wave(5, 1.2))))],
                     cam=(1.3, 760, 760, 1.0, 960, 540), dyn=multi(sparkles_dyn(700, 900, 60, 6, "front", (220, 240, 255))))
    if shot == "S02":
        def m(t, d):
            if t < 1.6: return dict(dx=lerp(500, 0, ease(t / 1.6)), dy=-abs(math.sin(math.pi * 2 * t)) * 50, pose="pip_front")
            return dict(pose="pip_front" if t < 2.4 else "pip_worried")
        return Scene("garden", chars=[Char("pip_front", 960, 1010, 560, who=P, motion=m)], cam=(1.1, 960, 560, 1.1, 960, 560))
    if shot == "S03":
        @functools.lru_cache(None)
        def base_img():
            k = 2
            im = gradient(W * k, H * k, SKY_TOP, SKY_LOW, 0, H * k)
            im.alpha_composite(rainbow_layer(W * k, H * k, 960 * k, 2300 * k, 2050 * k, 120 * k, 0.0))
            d = ImageDraw.Draw(im); cloud(d, 200 * k, 900 * k, 160 * k); cloud(d, 1750 * k, 950 * k, 180 * k)
            return im.resize((W, H), Image.LANCZOS)
        def dyn(im, dr, t, d, layer):
            if layer == "front" and t < 2.4:
                a = max(0, 1 - abs(t - 1.0) / 1.2)
                sparkle(dr, 960, 2300 - 2050 + 120 * 4 + 60, 60 * a, int(255 * a), (200, 225, 255))
        return Scene(base=lambda t, d: base_img(), dyn=dyn, cam=(1.0, 960, 540, 1.12, 960, 480))
    if shot == "S04":
        return "title"
    if shot == "S05":
        return Scene("garden", chars=[Char("milo_front", 960, 1150, 900, who=M, motion=combine(wave(6, 1.3), seq((0, {}), (4.5, hop(60, 1.5, 0, 0.66)))))])
    if shot == "S06":
        return Scene("garden", chars=[Char("pip_happy", 960, 1150, 900, who=P, motion=wave(5, 1.0))])
    if shot == "S07":
        return Scene("garden", chars=[Char("milo_back", 830, 1060, 380, who=M, motion=seq((0, {}), (2.5, dict(rot=6)), (5, dict(rot=-4)))),
                                      Char("pip_back", 1090, 1070, 440, who=P, motion=seq((0, {}), (3.0, dict(rot=-6)), (5.5, dict(rot=4))))],
                     cam=(1.0, 960, 540, 1.15, 960, 420))
    if shot == "S08":
        return Scene("garden", chars=[Char("pip_tilt", 760, 1110, 640, who=P, motion=lambda t, d: dict(dy=-abs(math.sin(math.pi * t * 1.1)) * 14 if 0.5 < t < 5 else 0))],
                     cam=(1.0, 960, 540, 1.0, 960, 540))
    if shot == "S09":
        return Scene("garden", chars=[Char("milo_front", 960, 1130, 780, who=M, motion=seq((0, {}), (1.2, dict(sx=1.05, sy=1.04)), (2.3, lambda t, d: dict(sx=1 + 0.04 * math.sin(t * 25), dy=-abs(math.sin(t * 6)) * 20))))])
    if shot == "S10":
        return Scene("garden", chars=[Char("pip_front", 760, 1000, 520, who=P, motion=seq((0, {}), (1.0, dict(pose="pip_tilt", dy=-20))))],
                     dyn=card_glow(1250, 960, 1.6), cam=(1.05, 860, 560, 1.25, 1150, 800))
    if shot == "S11":
        return Scene("garden", chars=[Char("milo_front", 900, 990, 380, who=M, motion=lambda t, d: dict(dx=lerp(-260, 0, ease(min(1, t / 1.2))), dy=-abs(math.sin(math.pi * 2 * t)) * 35 if t < 1.2 else 0)),
                                      Char("pip_front", 640, 1000, 420, who=P, motion=lambda t, d: dict(dx=lerp(-300, 0, ease(min(1, t / 1.3))), dy=-abs(math.sin(math.pi * 1.8 * t)) * 45 if t < 1.3 else 0))],
                     dyn=card_glow(1120, 990, 1.4, until=1.8), cam=(1.0, 960, 540, 1.1, 960, 640))
    if shot == "S12": return card_shot("tulips", "milo")
    if shot in ("S13", "S20", "S28", "S34"):
        nm = {"S13": "path", "S20": "path", "S28": "sunflowers", "S34": "sunflowers"}[shot]
        if shot == "S20": nm = "garden"
        spd = 1.1 if shot == "S34" else 1.0
        def cam_move(t, d):
            return None
        sc = Scene(nm, wide=2, chars=[Char("milo_side", 620, 1010, 400, who=M, motion=lambda t, d: dict(dx=lerp(0, 1500, t / d * spd), dy=-abs(math.sin(math.pi * 1.9 * spd * t)) * 45)),
                                      Char("pip_side", 360, 1020, 460, who=P, motion=lambda t, d: dict(dx=lerp(0, 1500, t / d * spd), dy=-abs(math.sin(math.pi * 1.8 * spd * t + 0.8)) * 55))],
                   cam=(1.0, 960, 540, 1.0, 960 + 1500 * spd, 540))
        if shot == "S20":
            base_dyn = None
            def dyn(im, dr, t, d, layer):
                if layer == "back":
                    dr.ellipse((3100, 800, 3900, 1060), fill=(120, 185, 228)); lilypad(dr, 3300, 900, 70); lilypad(dr, 3550, 960, 60)
            sc.dyn = dyn
        return sc
    if shot in ("S14", "S46"):
        sc = Scene("tulips", front="tulips", chars=[Char("milo_front", 800, 960, 380, who=M, motion=seq((0, {}), (1.0, hop(25, 2.0, 0, 1.0)))),
                                                   Char("pip_front", 1110, 970, 420, who=P, motion=seq((0, {}), (1.0, dict(pose="pip_happy", dy=-14))))],
                   cam=(1.15, 960, 380, 1.0, 960, 540))
        if shot == "S46": sc.post = dot(RAIN[0]); sc.chars = []; sc.cam = (1.0, 960, 540, 1.08, 960, 500)
        return sc
    if shot == "S15":
        return Scene("tulips", front="tulips", chars=[Char("milo_front", 960, 1130, 720, who=M, motion=seq((0, wave(4, 1)), (2.3, dict(rot=8, dx=10)), (3.0, lambda t, d: dict(rot=8, dy=-abs(math.sin(t * 2.4)) * 10))))])
    if shot == "S16":
        return Scene("tulips", front="tulips", chars=[Char("pip_happy", 960, 1110, 680, who=P, motion=hop(90, 1.4, 0.2, 3.0))])
    if shot == "S17":
        def m(t, d):
            if t < 3.6: return dict(dx=lerp(0, 60, ease(t / 2)))
            if t < 4.6: return dict(dx=60, rot=-4 * math.sin((t - 3.6) * 30), sy=0.95)
            return dict(dx=60, pose="milo_surprised")
        def dyn(im, dr, t, d, layer):
            if layer != "back": return
            wig = 0.35 * math.sin((t - 4.0) * 24) * math.exp(-(t - 4.0) * 2) if t > 4.0 else 0.03 * math.sin(t * 2)
            tulip(dr, 1330, 1150, 3.4, wig); tulip(dr, 1560, 1180, 3.0, -wig * 0.8)
        return Scene("tulips", chars=[Char("milo_side", 760, 1180, 760, who=M, motion=m)], dyn=dyn)
    if shot == "S18":
        def dyn(im, dr, t, d, layer):
            if layer == "back" and t < 2.8:
                card_glow(1300, 860, 1.6)(im, dr, t, d, "back")
        return Scene("tulips", front="tulips", chars=[Char("pip_tilt", 820, 1060, 620, who=P, motion=seq((0, {}), (2.6, dict(pose="pip_happy", dx=80))))],
                     dyn=dyn, cam=(1.0, 960, 540, 1.12, 1000, 600))
    if shot == "S19": return card_shot("pond", "pip")
    if shot in ("S21", "S47"):
        def dyn(im, dr, t, d, layer):
            if layer != "back": return
            for i, (x, y, r) in enumerate([(560, 860, 110), (1000, 940, 130), (1400, 850, 100), (820, 1030, 90), (1560, 990, 120)]):
                lilypad(dr, x, y + 6 * math.sin(t * 1.8 + i), r)
        sc = Scene("pond", dyn=multi(dyn, sparkles_dyn(960, 900, 600, 12, "front")), cam=(1.15, 760, 600, 1.15, 1160, 600))
        if shot == "S47": sc.post = dot(RAIN[3])
        return sc
    if shot in ("S22", "S23", "S24", "S25", "S27"):
        def pads(im, dr, t, d, layer):
            if layer != "back": return
            for i, (x, y, r) in enumerate([(1350, 900, 150), (1650, 980, 120)]):
                lilypad(dr, x, y + 5 * math.sin(t * 1.8 + i), r)
        if shot == "S22":
            return Scene("pond", dyn=pads, chars=[Char("pip_tilt", 700, 1120, 640, who=P, motion=seq((0, {}), (2.2, dict(rot=-6))))])
        if shot == "S23":
            return Scene("pond", dyn=pads, chars=[Char("milo_front", 700, 1060, 500, who=M, motion=seq((0, {}), (0.5, dict(rot=-8, dx=20)))),
                                                  Char("pip_happy", 1080, 1070, 560, who=P, motion=seq((0, {}), (1.6, hop(30, 1.5, 0, 0.7))))])
        if shot == "S24":
            def m(t, d):
                if t < 1.0: return dict(dx=lerp(-260, 0, ease(t)), dy=-abs(math.sin(math.pi * t)) * 80)
                w = math.exp(-(t - 1.0) * 0.6)
                r = dict(rot=14 * math.sin((t - 1.0) * 7) * w, sx=1 + 0.05 * math.sin(t * 22) * w)
                return r
            def padm(im, dr, t, d, layer):
                if layer != "back": return
                wob = 14 * math.sin((t - 1) * 7) * math.exp(-(t - 1) * 0.6) if t > 1 else 0
                lilypad(dr, 960, 1000 + wob * 0.4, 260)
            return Scene("pond", dyn=padm, chars=[Char("milo_front", 960, 1010, 460, who=M, motion=m)], shadows=False)
        if shot == "S25":
            def dyn(im, dr, t, d, layer):
                if layer != "back": return
                lilypad(dr, 760, 1000, 260); lilypad(dr, 1400, 930, 170)
                if t < 3.6: card_glow(1400, 905, 1.5)(im, dr, t, d, "back")
            return Scene("pond", dyn=dyn, chars=[Char("milo_front", 760, 1010, 460, who=M, motion=seq((0, {}), (1.2, dict(rot=-10, dx=30)), (3.6, hop(20, 2, 0, 1))))],
                         shadows=False, cam=(1.0, 960, 540, 1.12, 1050, 640))
        if shot == "S27":
            def dyn(im, dr, t, d, layer):
                if layer == "back": lilypad(dr, 760, 1000, 240)
            def mm(t, d):
                if t < 0.6: return dict(pose="milo_front")
                if t < 1.4: return dict(dx=lerp(0, 380, ease((t - 0.6) / 0.8)), dy=-math.sin(math.pi * (t - 0.6) / 0.8) * 160)
                if t < 4: return dict(dx=380)
                return dict(dx=380 + (t - 4) * 400, pose="milo_side", dy=-abs(math.sin(math.pi * 2 * t)) * 30)
            def pm(t, d):
                if t < 4.2: return {}
                return dict(dx=(t - 4.2) * 420, pose="pip_side", dy=-abs(math.sin(math.pi * 2 * t)) * 40)
            return Scene("pond", dyn=dyn, chars=[Char("milo_front", 760, 1010, 380, who=M, motion=mm), Char("pip_front", 1420, 760, 300, who=P, motion=pm, z=-1)],
                         shadows=False)
    if shot == "S26": return card_shot("sunflowers", "milo")
    if shot in ("S29", "S48"):
        sc = Scene("sunflowers", chars=[Char("milo_back", 860, 1080, 340, who=M, motion=lambda t, d: dict(rot=3 * math.sin(t))),
                                        Char("pip_back", 1080, 1090, 400, who=P, motion=lambda t, d: dict(rot=-3 * math.sin(t + 1)))],
                   cam=(1.15, 960, 700, 1.15, 960, 470))
        if shot == "S48": sc.post = dot(RAIN[2]); sc.chars = []
        return sc
    if shot == "S30":
        def pipm(t, d): return dict(sy=1.0 - 0.03 * min(1, t / 1.5), rot=2 * math.sin(t * 5) if t > 1.5 else 0)
        def milom(t, d):
            if t < 1.5: return dict(dy=lerp(80, -150, ease(t / 1.5)) - math.sin(math.pi * t / 1.5) * 120, dx=lerp(-200, 0, ease(t / 1.5)))
            return dict(dy=-150 - min(30, (t - 1.5) * 20), rot=5 * math.sin(t * 4), dx=3 * math.sin(t * 5))
        def dyn(im, dr, t, d, layer):
            if layer == "back" and t < 6.5:
                card_glow(1060, 330, 1.4)(im, dr, t, d, "back")
        return Scene("sunflowers", chars=[Char("pip_back", 1000, 1080, 440, who=P, motion=pipm), Char("milo_back", 1000, 1000, 300, who=M, motion=milom, z=1)],
                     dyn=dyn, cam=(1.0, 960, 640, 1.08, 1000, 460))
    if shot == "S31":
        def mm(t, d):
            if t < 1.0: return dict(dy=-200, pose="milo_back")
            if t < 1.8: return dict(dy=lerp(-200, 0, ease((t - 1) / 0.8)), rot=lerp(0, 75, ease((t - 1) / 0.8)), dx=lerp(0, -200, (t - 1) / 0.8), pose="milo_front")
            return dict(rot=75 - 75 * ease((t - 2.6) / 0.8) if t > 2.6 else 75, dx=-200, pose="milo_front")
        def pm(t, d):
            if t < 1.2: return {}
            if t < 1.9: return dict(rot=lerp(0, -70, ease((t - 1.2) / 0.7)), dx=lerp(0, 160, (t - 1.2) / 0.7), pose="pip_front")
            return dict(rot=-70 + 70 * ease((t - 2.8) / 0.8) if t > 2.8 else -70, dx=160, pose="pip_happy")
        return Scene("sunflowers", chars=[Char("milo_back", 860, 1050, 340, who=M, motion=mm), Char("pip_back", 1060, 1060, 420, who=P, motion=pm)])
    if shot == "S32": return card_shot("pinwheel", "pip")
    if shot == "S33":
        def dyn(im, dr, t, d, layer):
            if layer == "back":
                g = 0.5 + 0.5 * math.sin(t * 3)
                pinwheel(dr, 1500, 470, 16, t * 10, 0.4 + 0.4 * g)
                sparkle(dr, 1520, 450, 16 * g, int(255 * g))
        def pm(t, d): return dict(rot=-8 if t > 1.0 else 0, dy=-abs(math.sin(t * 5)) * 12 if t > 1 else 0)
        @functools.lru_cache(None)
        def base_img():
            k = 2; w, h = W * k, H * k
            im = set_image("garden").copy()
            d = ImageDraw.Draw(im)
            # long receding fence toward the far post
            for i in range(26):
                f = i / 25; x = lerp(0, 1480, f ** 0.6); ht = lerp(320, 60, f ** 0.6); y = lerp(1010, 560, f ** 0.6)
                w_ = lerp(70, 10, f ** 0.6)
                d.polygon([(x, y), (x, y - ht * 0.88), (x + w_ / 2, y - ht), (x + w_, y - ht * 0.88), (x + w_, y)], fill=(255, 255, 255), outline=(215, 215, 215))
            d.line((0, 1010 - 230, 1500, 560 - 40), fill=(250, 250, 248), width=12)
            d.line((1500, 470, 1500, 545), fill=(150, 110, 70), width=3)
            for i, x in enumerate([1600, 1780]):
                sunflower(d, x, 760, 0.8, 520)
            return im
        return Scene(base=lambda t, d: base_img(), dyn=dyn, chars=[Char("pip_back", 380, 1250, 860, who=P, motion=pm)], cam=(1.0, 960, 540, 1.18, 1250, 520))
    if shot == "S35":
        return Scene("fenceend", dyn=pinwheel_dyn(1220, 200, 120, lambda t, d: 8 * math.sin(t * 0.8), lambda t, d: 0.4 + 0.2 * math.sin(t * 2)),
                     cam=(1.7, 1200, 360, 1.8, 1240, 360))
    if shot in ("S36", "S37", "S38", "S39", "S40", "S49"):
        pw = dict(S36=lambda t, d: 0, S37=lambda t, d: 0, S38=lambda t, d: (25 * ease((t - 3.2) / 1.5)) if t > 3.2 else 0,
                  S39=lambda t, d: 25, S40=lambda t, d: 25 + (t ** 2) * 160 if t < 2 else 25 + 640 + (t - 2) * 1400,
                  S49=lambda t, d: t * 1400)[shot]
        gl = dict(S40=lambda t, d: min(1, t / 2.5), S49=lambda t, d: 1.0).get(shot, lambda t, d: 0.3)
        dyn = pinwheel_dyn(1220, 200, 120, pw, gl)
        if shot in ("S40", "S49"):
            dyn = multi(dyn, sparkles_dyn(1220, 200, 220, 14, "front", (200, 225, 255)))
        if shot in ("S38", "S40"):
            def puff(im, dr, t, d, layer, t0=2.6 if shot == "S38" else 0.5, x0=1000 if shot == "S38" else 1060):
                if layer != "front" or not (t0 < t < t0 + 1.4): return
                p = (t - t0) / 1.4
                for k in range(4):
                    x = x0 + p * 160 + k * 18; y = 260 + 20 * math.sin(k + p * 8)
                    dr.arc((x - 30, y - 18 - k * 8, x + 30, y + 18 + k * 8), -40, 40, fill=(255, 255, 255, int(220 * (1 - p))), width=6)
            dyn = multi(dyn, puff)
        cam = (1.45, 1150, 420, 1.45, 1150, 420)
        chars = []
        if shot == "S36":
            chars = [Char("milo_front", 900, 690, 330, who=M, motion=seq((0, wave(4, 1)), (2.2, dict(rot=8)))), Char("pip_tilt", 1500, 690, 360, who=P)]
        if shot == "S37":
            chars = [Char("milo_front", 900, 690, 330, who=M, motion=lambda t, d: dict(sx=1 + 0.04 * math.sin(t * 20), dy=-abs(math.sin(t * 4)) * 25)), Char("pip_happy", 1500, 690, 360, who=P, motion=hop(70, 1.4, 0.2, 3.5))]
        if shot == "S38":
            chars = [Char("milo_side", 960, 700, 380, who=M, motion=seq((0, {}), (2.2, dict(sx=1.06, sy=1.03)), (2.6, {})))]
            cam = (1.6, 1100, 380, 1.6, 1100, 380)
        if shot == "S39":
            chars = [Char("milo_side", 960, 700, 380, who=M, motion=seq((0, {}), (2.0, dict(rot=6)), (3.0, {}), (5.0, dict(sx=1.06, sy=1.04)))),
                     Char("pip_side", 1500, 700, 420, flip=True, who=P, motion=lambda t, d: dict(dx=lerp(260, 0, ease(t / 1.5)), sx=1.05 if t > 5 else 1))]
            cam = (1.4, 1220, 420, 1.55, 1220, 400)
        if shot in ("S40", "S49"):
            chars = [Char("milo_side", 1020, 700, 380, who=M, motion=lambda t, d: dict(sx=1.06 if 0.4 < t < 2.5 else 1)),
                     Char("pip_side", 1420, 700, 420, flip=True, who=P, motion=lambda t, d: dict(sx=1.06 if 0.4 < t < 2.5 else 1))]
            cam = (1.5, 1220, 380, 1.75, 1220, 330)
        sc = Scene("fenceend", chars=chars, dyn=dyn, cam=cam)
        if shot == "S49":
            sc.post = dot(BLUE); sc.chars = []; sc.cam = (1.75, 1220, 330, 1.8, 1220, 320)
        return sc
    if shot == "S41":
        def ribbon(im, dr, t, d, layer):
            if layer != "front": return
            if t < 4:  # A: rises from the pinwheel
                p = t / 4
                pts = [(1220 + 40 * math.sin(i * 0.25 + t * 4), 200 - i * 14) for i in range(int(4 + 60 * p))]
                for w_, a in ((40, 50), (22, 120), (10, 255)):
                    if len(pts) > 1: dr.line(pts, fill=(120, 180, 255, a), width=w_, joint="curve")
                pinwheel(dr, 1220, 200, 120, t * 1400, 1.0)
            else:  # B: flies across the sky toward the rainbow
                p = (t - 4) / 4
                head = (lerp(200, 1500, p), lerp(900, 200, p) - 200 * math.sin(p * math.pi))
                pts = [(head[0] - i * 22, head[1] + i * 10 + 30 * math.sin(i * 0.3 + t * 5)) for i in range(40)]
                for w_, a in ((44, 50), (24, 120), (10, 255)):
                    dr.line(pts, fill=(120, 180, 255, a), width=w_, joint="curve")
                sparkle(dr, head[0], head[1], 30, 255)
        def base(t, d):
            return set_image("fenceend") if t < 4 else set_sky()
        sc = Scene(base=base, dyn=multi(ribbon), cam=None)
        def camf(im, t, d):
            if t < 4:
                z = 1.75; fy = lerp(330, 200, ease(t / 4)); fx = 1220
                cw, ch = W / z, H / z
                return im.resize((W, H), Image.BICUBIC, box=(fx - cw / 2, max(0, fy - ch / 2), fx + cw / 2, max(0, fy - ch / 2) + ch))
            return im
        sc.post = camf
        return sc
    if shot == "S42":
        def base(t, d):
            fill = ease((t - 0.5) / 2.6)
            return sky_with(round(fill, 2))
        def dyn(im, dr, t, d, layer):
            if layer != "front": return
            fill = ease((t - 0.5) / 2.6)
            if 0 < fill < 1:
                a = math.radians(180 + 180 * fill); r = 760 - 4 * 44
                sparkle(dr, 960 + math.cos(a) * r, 720 + math.sin(a) * r, 40, 255)
            if t > 3.0:
                sparkles_dyn(960, 300, 700, 22, "front")(im, dr, t, d, "front")
        return Scene(base=base, dyn=dyn, cam=(1.0, 960, 540, 1.08, 960, 500))
    if shot == "S43":
        return Scene("garden", rain="full", chars=[Char("milo_front", 820, 990, 330, who=M, motion=hop(90, 1.6, 0, 4.5)),
                                                   Char("pip_happy", 1110, 1000, 420, who=P, motion=hop(110, 1.4, 0.3, 4.5))],
                     cam=(1.2, 960, 720, 1.0, 960, 540))
    if shot == "S44":
        return Scene("garden", rain="full", chars=[Char("milo_back", 900, 1080, 360, who=M, motion=lambda t, d: dict(rot=-6)),
                                                   Char("pip_back", 1060, 1090, 420, who=P, motion=lambda t, d: dict(rot=7))],
                     cam=(1.0, 960, 540, 1.1, 960, 460))
    if shot == "S45":
        return Scene("garden", rain="full", chars=[Char("milo_front", 780, 1100, 560, who=M), Char("pip_front", 1160, 1110, 640, who=P)])
    if shot == "S50":
        return Scene("garden", rain="full", chars=[Char("milo_front", 780, 1100, 560, who=M, motion=wave(7, 1.4)), Char("pip_happy", 1160, 1110, 640, who=P, motion=wave(6, 1.2))],
                     cam=(1.12, 960, 600, 1.0, 960, 540))
    if shot == "S51":
        def mm(t, d): return dict(dy=lerp(0, -260, t / d) - abs(math.sin(math.pi * 1.6 * t)) * 30 * (1 - t / d), scale=lerp(1, 0.3, t / d), dx=lerp(0, 60, t / d))
        def pm(t, d): return dict(dy=lerp(0, -260, t / d) - abs(math.sin(math.pi * 1.5 * t + 0.6)) * 36 * (1 - t / d), scale=lerp(1, 0.3, t / d), dx=lerp(0, -40, t / d))
        return Scene("path", rain="full", chars=[Char("milo_back", 860, 1060, 380, who=M, motion=mm), Char("pip_back", 1080, 1070, 440, who=P, motion=pm)],
                     cam=(1.0, 960, 540, 1.15, 960, 380))
    if shot == "S52":
        return "end"
    raise ValueError(shot)

@functools.lru_cache(None)
def set_sky():
    k = 2
    im = gradient(W * k, H * k, SKY_TOP, SKY_LOW, 0, H * k)
    im.alpha_composite(rainbow_layer(W * k, H * k, 960 * k, 720 * k, 760 * k, 44 * k, 0.0))
    d = ImageDraw.Draw(im)
    for (x, y, s) in [(260, 170, 70), (1580, 130, 85), (1240, 300, 50), (520, 360, 45), (900, 900, 120), (1700, 850, 100)]:
        cloud(d, x * k, y * k, s * k)
    return im.resize((W, H), Image.LANCZOS)

@functools.lru_cache(None)
def sky_with(fill):
    k = 2
    im = gradient(W * k, H * k, SKY_TOP, SKY_LOW, 0, H * k)
    im.alpha_composite(rainbow_layer(W * k, H * k, 960 * k, 720 * k, 760 * k, 44 * k, fill))
    d = ImageDraw.Draw(im)
    for (x, y, s) in [(260, 170, 70), (1580, 130, 85), (1240, 300, 50), (520, 360, 45), (900, 900, 120), (1700, 850, 100)]:
        cloud(d, x * k, y * k, s * k)
    return im.resize((W, H), Image.LANCZOS)

# ------------------------------------------------------------------ title + end screen
def title_frames(n):
    s01 = build("S01")
    last = s01.frame(5.99, 6, 5.99).convert("RGB").filter(ImageFilter.GaussianBlur(10))
    for i in range(n):
        t = i / FPS
        im = last.copy().convert("RGBA")
        e = ease(t / 1.0)
        sc = 0.6 + 0.4 * e + 0.015 * math.sin(t * 3)
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
        for line, y, size in (("Milo and the", 360, 110), ("Missing Rainbow Color", 520, 140)):
            f = ImageFont.truetype(FONT, size); f.set_variation_by_name("Bold")
            w_ = d.textlength(line, font=f)
            x = (W - w_) / 2
            d.text((x, y), line, font=f, fill=(255, 255, 255), stroke_width=18, stroke_fill=(255, 255, 255))
            # rainbow letters
            cx = x
            for j, ch in enumerate(line):
                d.text((cx, y), ch, font=f, fill=[(235, 90, 100), (245, 150, 60), (230, 180, 30), (90, 175, 85), (70, 130, 230), (150, 100, 210)][j % 6])
                cx += d.textlength(ch, font=f)
        tw = txt.resize((int(W * sc), int(H * sc)), Image.BICUBIC)
        a = int(255 * e)
        tw.putalpha(tw.getchannel("A").point(lambda v: v * a // 255))
        im.alpha_composite(tw, ((W - tw.width) // 2, (H - tw.height) // 2))
        if t > 0.4:
            dr = ImageDraw.Draw(im, "RGBA")
            for k in range(8):
                p = ((t - 0.4) * 0.8 + k / 8) % 1
                sparkle(dr, 300 + k * 190, 300 + 400 * ((k * 37) % 7) / 7, 26 * math.sin(math.pi * p), int(255 * math.sin(math.pi * p)))
        yield im.convert("RGB")

def end_frames(n):
    bg = set_image("garden", "full").convert("RGB").filter(ImageFilter.GaussianBlur(14))
    d = ImageDraw.Draw(bg, "RGBA")
    # space for YouTube end-screen elements: two video cards + a subscribe button
    for x in (330, 1010):
        d.rounded_rectangle((x, 430, x + 580, 430 + 326), radius=30, fill=(255, 255, 255, 60), outline=(255, 255, 255, 170), width=5)
    d.ellipse((860, 140, 1060, 340), fill=(255, 255, 255, 60), outline=(255, 255, 255, 170), width=5)
    for i in range(n):
        t = i / FPS
        im = bg.copy(); dr = ImageDraw.Draw(im, "RGBA")
        for k in range(10):
            ph = (t * 0.5 + k / 10) % 1
            sparkle(dr, 120 + k * 180, 900 + 40 * math.sin(k), 22 * math.sin(math.pi * ph), int(230 * math.sin(math.pi * ph)))
        fade = min(1, max(0, (14 - t) / 3))
        out = im
        if fade < 1:
            out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, fade)
        yield out

# ------------------------------------------------------------------ render
def render_shot(shot):
    s = SH[shot]; d = s["end"] - s["start"]; n = d * FPS
    path = os.path.join(SEG, shot + ".mp4")
    if os.path.exists(path) and os.environ.get("REUSE"):
        return path
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    sc = build(shot)
    if sc == "title":
        it = title_frames(n)
    elif sc == "end":
        it = end_frames(n)
    else:
        it = (sc.frame(i / FPS, d, s["start"] + i / FPS).convert("RGB") for i in range(n))
    for im in it:
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    return path

def main():
    only = sys.argv[1:]
    todo = only or [s["shot"] for s in shots]
    with Pool(4) as pool:
        for pth in pool.imap_unordered(render_shot, todo):
            print("done", os.path.basename(pth), flush=True)
    if only:
        return
    lst = os.path.join(SEG, "list.txt")
    with open(lst, "w") as f:
        for s in shots:
            f.write(f"file '{os.path.join(SEG, s['shot'] + '.mp4')}'\n")
    final = os.path.join(HERE, "..", "ep1_milo_and_the_missing_rainbow_color.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", "360", "-movflags", "+faststart", final], check=True)
    print("final", final)

if __name__ == "__main__":
    main()
