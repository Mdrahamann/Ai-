"""Render Episode 2, Milo and the Windy Day (6:00, 1920x1080, 24 fps), from ../plan.py and out/lines.json.

Characters are the pose cutouts from Episode 1 (ep1/build/cutouts). Sets, the paper windmill, wind, captions
and icons are drawn here. Usage: python3 audio.py && python3 render.py  (python3 render.py S14 S15 renders single shots)
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
    im = Image.open(os.path.join(CUT, pose + ".png")).convert("RGBA")
    im = im.resize((max(1, round(im.width * h / im.height)), int(h)), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if tint:  # frustration: warmer, redder
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

BLADE = [(235, 85, 90), (255, 200, 60), (110, 190, 95), (80, 145, 235)]

def blade_poly(cx, cy, s, a):
    u = (math.cos(a), math.sin(a)); v = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
    return [(cx, cy), (cx + u[0] * s, cy + u[1] * s), (cx + (u[0] * 0.55 + v[0] * 0.75) * s, cy + (u[1] * 0.55 + v[1] * 0.75) * s)]

def draw_blade(d, cx, cy, s, a, col, state="ok"):
    p = blade_poly(cx, cy, s, a)
    d.polygon(p, fill=col, outline=(70, 60, 60), width=max(2, int(s * 0.025)))
    if state in ("torn", "worse"):
        # jagged rip from the outer edge toward the hub
        (x0, y0), (x1, y1), (x2, y2) = p
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        L = 0.45 if state == "torn" else 0.8
        pts = []
        for i in range(8):
            f = i / 7 * L
            px, py = lerp(mx, x0, f), lerp(my, y0, f)
            k = 1 if i % 2 else -1
            pts.append((px + k * s * 0.05 * math.sin(a), py - k * s * 0.05 * math.cos(a)))
        d.line(pts, fill=(255, 250, 240), width=max(3, int(s * 0.05)))
        d.line(pts, fill=(60, 50, 60), width=max(1, int(s * 0.012)))
    if state == "patched":
        (x0, y0), (x1, y1), (x2, y2) = p
        mx, my = lerp(x0, (x1 + x2) / 2, 0.62), lerp(y0, (y1 + y2) / 2, 0.62)
        ps = s * 0.34
        for i, c in enumerate([(235, 85, 90), (255, 170, 70), (255, 220, 80), (110, 190, 95), (80, 145, 235), (160, 110, 210)]):
            off = (i - 2.5) * ps / 6
            q = [(mx - ps / 2 + off * 0, my - ps / 2 + (i) * ps / 6), (mx + ps / 2, my - ps / 2 + i * ps / 6),
                 (mx + ps / 2, my - ps / 2 + (i + 1) * ps / 6), (mx - ps / 2, my - ps / 2 + (i + 1) * ps / 6)]
            d.polygon(q, fill=c)
        d.rectangle((mx - ps / 2, my - ps / 2, mx + ps / 2, my + ps / 2), outline=(255, 255, 255), width=max(2, int(s * 0.02)))

def windmill(d, x, y, s, ang=0.0, state="full", blades=4, stick=True, blur=0.0, stick_len=2.2):
    """x,y = hub. state: full | torn | worse | patched. blades: how many are attached (red, yellow, green, blue)."""
    if stick:
        d.line((x, y, x, y + s * stick_len), fill=(160, 115, 70), width=max(4, int(s * 0.07)))
    if blur > 0.3:  # spinning fast: a rainbow ring
        for i, c in enumerate([(235, 85, 90), (255, 170, 70), (255, 210, 80), (110, 190, 95), (80, 145, 235), (160, 110, 210)]):
            r = s * (1.0 - i * 0.12)
            d.ellipse((x - r, y - r, x + r, y + r), outline=c + (int(200 * blur),), width=max(3, int(s * 0.1)))
    for i in range(blades):
        a = math.radians(ang + i * 90)
        st = "ok"
        if i == 3: st = {"torn": "torn", "worse": "worse", "patched": "patched"}.get(state, "ok")
        if i == 3 and state == "worse":  # the blue blade hangs loose, bent down
            draw_blade(d, x + s * 0.05, y + s * 0.05, s * 0.95, math.radians(100 + 6 * math.sin(ang * 0.05)), BLADE[3], "worse")
            continue
        draw_blade(d, x, y, s, a, BLADE[i] + ((255,) if blur < 0.3 else (int(255 * (1 - blur * 0.7)),)), st)
    d.ellipse((x - s * 0.09, y - s * 0.09, x + s * 0.09, y + s * 0.09), fill=(255, 220, 90), outline=(90, 70, 50), width=2)

def loose_blade(d, x, y, s, a_deg, state="ok", crumple=0.0):
    if crumple > 0.5:
        r = s * 0.35
        pts = [(x + math.cos(k) * r * (0.8 + 0.25 * math.sin(k * 5)), y + math.sin(k) * r * (0.8 + 0.25 * math.cos(k * 4))) for k in np.linspace(0, 2 * math.pi, 14)]
        d.polygon(pts, fill=BLADE[3], outline=(60, 50, 60)); return
    draw_blade(d, x, y, s, math.radians(a_deg), BLADE[3], state)

def sparkle(d, x, y, r, a=255, col=(255, 255, 255)):
    d.polygon([(x, y - r), (x + r * .22, y - r * .22), (x + r, y), (x + r * .22, y + r * .22), (x, y + r),
               (x - r * .22, y + r * .22), (x - r, y), (x - r * .22, y - r * .22)], fill=col + (int(a),))

def wind_lines(d, t, strength, seed=1):
    if strength <= 0.02: return
    rs = np.random.default_rng(seed)
    for k in range(int(10 * strength) + 2):
        y = rs.uniform(80, 900); spd = rs.uniform(900, 1500); ph = rs.uniform(0, 3000)
        x = (ph + t * spd * (0.6 + strength)) % 2600 - 400
        L = 160 + 120 * strength
        pts = [(x - L + i * L / 10, y + 14 * math.sin(i * 0.7 + t * 6)) for i in range(11)]
        d.line(pts, fill=(255, 255, 255, int(150 * min(1, strength))), width=5, joint="curve")

def grass_tips(d, t, wind, x0=560, x1=1920, y=560, seed=3):
    rs = np.random.default_rng(seed)
    for i in range(70):
        x = rs.uniform(x0, x1); h = rs.uniform(50, 110); ph = rs.uniform(0, 6)
        lean = (0.15 * math.sin(t * 1.3 + ph) + 0.9 * wind * (0.7 + 0.3 * math.sin(t * 7 + ph))) * h
        d.line((x, y, x + lean * 0.5, y - h * 0.55, x + lean, y - h), fill=(120, 175, 80), width=5)

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

# ------------------------------------------------------------------ sets
SKY0, SKY1 = (255, 205, 140), (255, 236, 205)

@functools.lru_cache(None)
def porch_set(table=False, pot=True):
    im = gradient(W, H, SKY0, SKY1); d = ImageDraw.Draw(im)
    d.ellipse((300, 420, 1500, 900), fill=(170, 205, 120)); d.ellipse((1000, 440, 2300, 920), fill=(155, 198, 110))
    d.rectangle((0, 560, W, 760), fill=(150, 195, 105))
    d.ellipse((1640, 90, 1800, 250), fill=(255, 238, 170))  # low sun
    # house wall
    d.rectangle((0, 0, 560, 780), fill=(248, 220, 192)); d.rectangle((540, 0, 575, 780), fill=(230, 196, 165))
    d.ellipse((150, 200, 410, 460), fill=(255, 255, 250)); d.ellipse((172, 222, 388, 438), fill=(190, 225, 245))
    d.line((280, 222, 280, 438), fill=(255, 255, 250), width=10); d.line((172, 330, 388, 330), fill=(255, 255, 250), width=10)
    # railing
    d.rectangle((575, 560, W, 584), fill=(255, 253, 248), outline=(220, 205, 190))
    for x in range(610, W, 72):
        d.rounded_rectangle((x, 584, x + 26, 770), radius=8, fill=(255, 253, 248), outline=(220, 205, 190))
    d.rectangle((575, 755, W, 775), fill=(250, 245, 238))
    # floor
    d.rectangle((0, 770, W, H), fill=(205, 150, 98))
    for i, y in enumerate([800, 840, 890, 950, 1020]):
        d.line((0, y, W, y), fill=(180, 128, 80), width=3)
    if pot:
        d.polygon([(1500, 560), (1620, 560), (1605, 470), (1515, 470)], fill=(215, 120, 80))
        d.rectangle((1505, 455, 1615, 480), fill=(230, 140, 95))
    if table:
        tablef(d, 960, 790, 360)
    return im

def tablef(d, x, y, r):
    d.rectangle((x - 18, y, x + 18, y + 190), fill=(150, 100, 60))
    d.ellipse((x - r, y - r * 0.18, x + r, y + r * 0.18), fill=(170, 115, 70))
    d.ellipse((x - r * 0.97, y - r * 0.2, x + r * 0.97, y + r * 0.13), fill=(195, 140, 88))

@functools.lru_cache(None)
def craft_set():
    im = gradient(W, H, (252, 240, 218), (245, 228, 200)); d = ImageDraw.Draw(im)
    d.rectangle((0, 640, W, H), fill=(232, 205, 170))
    d.rectangle((1300, 120, 1760, 540), fill=(255, 252, 245)); d.rectangle((1325, 145, 1735, 515), fill=(200, 230, 248))
    d.ellipse((1560, 190, 1680, 310), fill=(255, 240, 170))
    d.line((1530, 145, 1530, 515), fill=(255, 252, 245), width=12); d.line((1325, 330, 1735, 330), fill=(255, 252, 245), width=12)
    for k in range(4):  # sunbeams
        d.polygon([(1330 + k * 90, 520), (1420 + k * 90, 520), (1100 + k * 150, 1080), (980 + k * 150, 1080)], fill=(255, 245, 210))
    d.rectangle((120, 260, 520, 280), fill=(190, 140, 95))
    for i, c in enumerate([(235, 85, 90), (80, 145, 235), (255, 200, 60), (110, 190, 95)]):
        d.rectangle((150 + i * 90, 190, 210 + i * 90, 260), fill=c)
    return im

@functools.lru_cache(None)
def craft_table():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle((260, 860, 1660, H), fill=(170, 112, 66))
    d.ellipse((220, 760, 1700, 960), fill=(190, 130, 80)); d.ellipse((240, 752, 1680, 940), fill=(212, 154, 98))
    rs = np.random.default_rng(5)
    for i in range(9):
        x, y = rs.uniform(360, 1560), rs.uniform(800, 900); c = BLADE[i % 4]
        d.polygon([(x, y), (x + 70, y - 8), (x + 78, y + 40), (x + 6, y + 48)], fill=c)
    d.rounded_rectangle((420, 818, 470, 900), radius=10, fill=(250, 250, 250), outline=(120, 120, 140), width=3)  # glue stick
    d.ellipse((1400, 830, 1480, 880), outline=(200, 200, 205), width=14)  # tape
    d.line((1220, 880, 1320, 830), fill=(150, 150, 160), width=8); d.ellipse((1190, 870, 1230, 900), outline=(240, 90, 90), width=6)
    return L

@functools.lru_cache(None)
def step_layer():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle((0, 985, W, H), fill=(190, 135, 85)); d.line((0, 985, W, 985), fill=(225, 175, 120), width=8)
    d.line((0, 1040, W, 1040), fill=(165, 115, 70), width=3)
    return L

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
        if self.base in (porch_set,) or getattr(self.base, "porch", False):
            pass
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
            if wind > 0.3 and c.pose.startswith("pip"):
                st["rot"] += 2.5 * wind * math.sin(t * 9)
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

def bg_porch(table=False, pot=True): return lambda: porch_set(table, pot)
def bg_craft(): return craft_set()

def porch_back(wind_fn=None):
    def f(im, dr, t, d, wind):
        grass_tips(dr, t, wind)
    return f

def layer_wind(seed=1):
    def f(im, dr, t, d, wind): wind_lines(dr, t, wind, seed)
    return f

def layer_windmill(x, y, s, state, ang=lambda t, d: 6 * math.sin(t * 1.5), blades=4, stick=True, blur=lambda t, d: 0.0, stick_len=2.2):
    def f(im, dr, t, d, wind):
        st = state(t, d) if callable(state) else state
        b = blades(t, d) if callable(blades) else blades
        xx = x(t, d) if callable(x) else x; yy = y(t, d) if callable(y) else y
        windmill(dr, xx, yy, s, ang(t, d), st, b, stick, blur(t, d), stick_len)
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

# standard positions
PX, MX, BY = 700, 1220, 1010      # porch two-shot: Pip left, Milo right, floor baseline
PH, MH = 520, 420

def two_shot(pip="pip_front", milo="milo_side", pm=None, mm=None, milo_flip=True, py=BY, my=BY, ph=PH, mh=MH, px=PX, mx=MX):
    return [Char(pip, px, py, ph, who="Pip", motion=pm), Char(milo, mx, my, mh, flip=milo_flip if milo == "milo_side" else False, who="Milo", motion=mm)]

# ------------------------------------------------------------------ shots
def build(sid):
    P, M = "Pip", "Milo"
    porch = bg_porch(); porch_t = bg_porch(table=True)
    gb = porch_back()
    if sid in ("S01",):
        wind = lambda t, d: ramp(t, 1.5, 5.0) * 0.9
        def wm_state(t, d): return "full"
        return Scene(porch_t, back=gb, chars=[
            Char("pip_front", 760, 1020, 520, who=P),
            Char("milo_side", 1180, 1000, 420, flip=True, who=M, motion=lambda t, d: dict(dy=-30 - 10 * math.sin(t * 3), rot=4 if t < 2.4 else 0))],
            layers=[layer_windmill(960, 470, 150, "full", ang=lambda t, d: 10 * math.sin(t * 2) + 40 * ramp(t, 3, 5), blades=lambda t, d: 3 if t < 2.4 else 4, stick_len=2.1),
                    lambda im, dr, t, d, w: loose_blade(dr, lerp(1090, 960, ramp(t, 1.4, 2.4)), lerp(560, 470, ramp(t, 1.4, 2.4)), 150, lerp(150, 270, ramp(t, 1.4, 2.4))) if t < 2.4 else None,
                    layer_wind(1)], wind=wind)
    if sid in ("S02", "S13"):
        warp = 1.0 if sid == "S02" else 0.625
        def ang(t, d): t = t * warp; return 25 * math.sin(t * 9) * (1 if t < 1.0 else 0.5) + 20 * t
        return Scene(porch, back=gb, layers=[layer_windmill(960, 420, 330, lambda t, d: "full" if t * warp < 1.0 else "torn", ang=ang, stick_len=2.0),
                                             lambda im, dr, t, d, w: [sparkle(dr, 1100 + k * 40, 430 - k * 30, 26 * (1 - (t * warp - 1) * 2), 255 * max(0, 1 - (t * warp - 1) * 2)) for k in range(3)] if 1.0 <= t * warp < 1.5 else None,
                                             layer_wind(2)], wind=lambda t, d: 1.0 if t * warp < 2.2 else 0.5, cam=(1.0, 960, 540, 1.04, 960, 520))
    if sid == "S03":
        return Scene(porch, back=gb, chars=[Char("milo_surprised", 960, 1250, 900, who=M, motion=comb(const(tint=0.7, sx=1.06, sy=1.05), shake(6, 30)))],
                     layers=[lambda im, dr, t, d, w: bang(dr, 1330, 260, t, 0.3), lambda im, dr, t, d, w: puff_lines(dr, 640, 330, t, 1.0),
                             cap("FRUSTRATED", ["FRUSTRATED"], 0.5, 2.9, "top")], wind=0.3, cam=(1.0, 960, 540, 1.06, 960, 500))
    if sid in ("S04", "S23"):
        lift = (lambda t, d: dict(dy=-35 * ramp(t, 0.8, 1.8))) if sid == "S04" else (lambda t, d: dict(dy=-6 * math.sin(t * 2) if 1 < t < 2 else 0))
        def pose(t, d): return dict(pose="pip_front" if (sid == "S04" and t < 0.9) else "pip_worried")
        return Scene(porch, back=gb, chars=[Char("pip_front", 960, 1200, 880, who=P, motion=comb(lift, pose))],
                     front=lambda im, dr, t, d, w: (dr.line((960, H, 960, 720), fill=(160, 115, 70), width=16)), wind=0.15,
                     cam=(1.0, 960, 540, 1.0 if sid == "S04" else 1.05, 960, 520))
    if sid == "S05":
        return Scene(bg_craft, chars=[Char("pip_front", 720, 870, 520, who=P), Char("milo_front", 1130, 860, 450, who=M, motion=hop(15, 1.5))], front=img_layer(craft_table),
                     layers=[lambda im, dr, t, d, w: drawing(dr, 1390, 560 - 10 * math.sin(t * 3), 1.1), cap("THIS MORNING", ["MORNING"], 0.2, 3.4, "tag")],
                     cam=(1.0, 960, 540, 1.08, 960, 560))
    if sid == "S06":
        return Scene(bg_craft, chars=[Char("milo_front", 900, 1010, 640, who=M, motion=hop(40, 1.6))], front=img_layer(craft_table),
                     layers=[lambda im, dr, t, d, w: drawing(dr, 1330, 520 + 40 * math.sin(t * 5), 1.2, rot=12 * math.sin(t * 5))])
    if sid == "S07":
        return Scene(bg_craft, chars=[Char("pip_happy", 720, 870, 520, who=P), Char("milo_front", 1170, 860, 450, who=M, motion=hop(12, 1.2, 1.5, 3))], front=img_layer(craft_table),
                     layers=[lambda im, dr, t, d, w: dr.line((830, 900, 830, 520), fill=(160, 115, 70), width=12),
                             lambda im, dr, t, d, w: dr.polygon(blade_poly(1060, lerp(880, 700, ramp(t, 2.5, 3.5)), 90, math.radians(-30)), fill=BLADE[0])])
    if sid == "S08":
        def bl(t, d): return min(3, int(ramp(t, 0.0, 1.0) * 1) + (t > 3.5) + (t > 6.0)) if t > 1.0 else 0
        return Scene(bg_craft, front=img_layer(craft_table), layers=[layer_windmill(960, 470, 220, "full", ang=lambda t, d: -20, blades=lambda t, d: (t > 1.0) + (t > 3.5) + (t > 6.0), stick_len=1.9),
                     lambda im, dr, t, d, w: wing_pat(dr, 1180, 560, t), lambda im, dr, t, d, w: paws(dr, 960, 880)], cam=(1.25, 760, 520, 1.25, 1160, 520))
    if sid == "S09":
        def stuck(im, dr, t, d, w):
            fy = -abs(math.sin(t * 6)) * 40 if t > 1.2 else 0
            dr.polygon(blade_poly(1320, 560 + fy, 110, math.radians(-20 + 25 * math.sin(t * 6))), fill=BLADE[2], outline=(70, 60, 60))
        return Scene(bg_craft, chars=[Char("pip_happy", 720, 870, 520, who=P, motion=hop(14, 2.2, 4.4, 6.5)),
                                      Char("milo_front", 1180, 860, 450, who=M, motion=lambda t, d: dict(dy=-abs(math.sin(t * 6)) * 40 if t > 1.2 else 0, rot=5 * math.sin(t * 6)))],
                     front=img_layer(craft_table), layers=[stuck])
    if sid == "S10":
        def hat(im, dr, t, d, w):
            if t > 1.4: dr.polygon([(1165, 418), (1220, 410), (1216, 455), (1162, 460)], fill=BLADE[2], outline=(70, 60, 60))
        return Scene(bg_craft, chars=[Char("pip_happy", 740, 870, 520, who=P, motion=lambda t, d: dict(dx=150 * ramp(t, 0.2, 1.0) - 150 * ramp(t, 1.6, 2.4))),
                                      Char("milo_front", 1180, 860, 450, who=M, motion=hop(25, 2.4, 3.8, 6.8))],
                     front=img_layer(craft_table), layers=[lambda im, dr, t, d, w: hat(im, dr, t, d, w) if True else None], cam=(1.0, 960, 540, 1.1, 1060, 520))
    if sid == "S11":
        return Scene(bg_craft, chars=[Char("milo_front", 1200, 1000, 700, who=M, motion=const(sx=1.06, sy=1.04))], front=img_layer(craft_table),
                     layers=[layer_windmill(620, 420, 200, "full", ang=lambda t, d: -15, blades=3, stick_len=2.0),
                             lambda im, dr, t, d, w: loose_blade(dr, 1420, 720, 120, 250),
                             lambda im, dr, t, d, w: [sparkle(dr, 1000 + 120 * k, 300 + 60 * (k % 2), 22 * abs(math.sin(t * 2 + k)), 230) for k in range(4)]],
                     cam=(1.0, 960, 540, 1.1, 1100, 520))
    if sid == "S12":
        walk = lambda off: (lambda t, d: dict(dx=lerp(0, 820, t / d), dy=-abs(math.sin(math.pi * 2 * t + off)) * 22))
        return Scene(porch, back=gb, chars=[Char("milo_side", 160, 1010, 380, who=M, motion=walk(0.0)), Char("pip_side", 520, 1020, 470, who=P, motion=walk(0.7))],
                     layers=[lambda im, dr, t, d, w: windmill(dr, 380 + 820 * t / d, 640 - abs(math.sin(math.pi * 2 * t)) * 14, 110, 5 * math.sin(t * 3), "full", 3, True, 0, 2.0),
                             lambda im, dr, t, d, w: loose_blade(dr, 230 + 820 * t / d, 610, 80, 240)], wind=0.1)
    if sid == "S14":
        return Scene(porch, back=gb, chars=[Char("pip_front", 640, 1010, 520, who=P), Char("milo_back", 1260, 1000, 420, who=M, motion=const(tint=0.5))],
                     layers=[layer_windmill(800, 560, 120, "torn", ang=lambda t, d: 12, stick_len=3.3)], wind=0.2)
    if sid == "S15":
        return Scene(porch, back=gb, chars=[Char("milo_worried", 960, 1240, 880, who=M, motion=comb(const(tint=0.6, sx=1.05), lambda t, d: dict(dy=-18 if 1.2 < t < 1.4 else 0), shake(3, 22)))],
                     layers=[lambda im, dr, t, d, w: loose_blade(dr, 1290, 900, 200, 260, "torn"), lambda im, dr, t, d, w: puff_lines(dr, 650, 360, t, 0.8)], wind=0.2)
    if sid == "S16":
        def wmx(t, d): return lerp(820, 1080, ramp(t, 3.3, 4.2))
        return Scene(porch_t, back=gb, chars=[Char("pip_front", 640, 1010, 520, who=P, motion=lambda t, d: dict(dx=60 * ramp(t, 0.4, 1.4) - 60 * ramp(t, 3.4, 4.2))),
                                               Char("milo_side", 1300, 1000, 420, flip=True, who=M, motion=const(tint=0.6))],
                     layers=[layer_windmill(wmx, 560, 120, "torn", ang=lambda t, d: 12, stick_len=1.8),
                             lambda im, dr, t, d, w: dr.ellipse((1100, 760, 1180, 800), outline=(205, 205, 210), width=16) if t < 4.7 else dr.ellipse((1190, 700, 1270, 740), outline=(205, 205, 210), width=16)], wind=0.2)
    if sid == "S17":
        def tape(im, dr, t, d, w):
            for k in range(3):
                if t > 0.5 + k * 1.2:
                    a = math.radians(-30 + 40 * k + 25 * math.sin(t * 8 + k))
                    x, y = 1000 + (k - 1) * 130, 560 + k * 60
                    dr.line((x, y, x + math.cos(a) * 220, y + math.sin(a) * 220), fill=(225, 230, 240, 200), width=26)
        return Scene(porch_t, back=gb, chars=[Char("milo_front", 1000, 1060, 620, who=M, motion=comb(const(tint=0.6), shake(5, 20), lambda t, d: dict(rot=6 * math.sin(t * 7))))],
                     layers=[layer_windmill(640, 620, 120, "torn", ang=lambda t, d: 12, stick_len=1.4), tape], wind=0.15)
    if sid == "S18":
        def yank(im, dr, t, d, w):
            pull = 60 * ramp(t, 0.6, 1.4)
            for sx in (-1, 1):
                dr.ellipse((1000 + sx * (420 + pull) - 90, 620 - 70, 1000 + sx * (420 + pull) + 90, 620 + 70), fill=(250, 215, 80), outline=(200, 160, 50), width=3)
        def bl(im, dr, t, d, w):
            st = "torn" if t < 1.4 else "worse"
            a = 230 if st == "torn" else 230 + 50 * ramp(t, 1.4, 2.0)
            loose_blade(dr, 640, 760, 560, -28 if st == "torn" else -28 + 40 * ramp(t, 1.4, 2.0), st)
        return Scene(porch, back=gb, layers=[bl, yank], cam=(1.0, 960, 540, 1.04, 960, 540))
    if sid in ("S19", "S28"):
        tint = (lambda t, d: 0.0) if sid == "S19" else (lambda t, d: 0.4 * (1 - ramp(t, 1.0, 5.0)))
        lays = []
        if sid == "S28":
            lays = [lambda im, dr, t, d, w: loose_blade(dr, 1320, 960, 230, 255, "worse", crumple=1.0 if t < 2.6 else 0.0)]
        return Scene(porch, back=gb, chars=[Char("milo_worried", 960, 1260, 920, who=M, motion=lambda t, d: dict(tint=tint(t, d)))], layers=lays,
                     cam=(1.0, 960, 540, 1.07, 960, 480))
    if sid == "S20":
        def leaf(im, dr, t, d, w):
            x = -80 + t * 300; y = 300 + 90 * math.sin(t * 1.4) + t * 30
            dr.ellipse((x - 26, y - 12, x + 26, y + 12), fill=(235, 150, 60))
        return Scene(porch_t, back=gb, chars=[Char("pip_front", 520, 1010, 430, who=P), Char("milo_front", 1400, 1000, 350, who=M)],
                     layers=[layer_windmill(960, 560, 110, "worse", ang=lambda t, d: 8 + 3 * math.sin(t * 2), stick_len=2.0), leaf], wind=0.08,
                     cam=(1.0, 960, 540, 1.06, 960, 560))
    if sid == "S21":
        def roll(im, dr, t, d, w):
            x = 1150 + max(0, t - 0.6) * 260; y = 960 - abs(math.sin(max(0, t - 0.6) * 4)) * 40 * math.exp(-(t - 0.6))
            if t > 0.6: dr.ellipse((x - 45, y - 45, x + 45, y + 45), outline=(205, 205, 210), width=18)
        return Scene(porch, back=gb, chars=[Char("milo_front", 900, 1060, 660, who=M, motion=comb(const(tint=0.8, sx=1.06),
                     lambda t, d: dict(dy=-30 if (0.4 < t < 0.6 or 3.3 < t < 3.5 or 3.8 < t < 4.0) else 0), shake(4, 24)))],
                     layers=[roll, lambda im, dr, t, d, w: puff_lines(dr, 640, 470, t, 1.0)], wind=0.1)
    if sid == "S22":
        return Scene(porch, back=gb, chars=[Char("milo_side", 980, 1150, 640, who=M, motion=lambda t, d: dict(sy=0.94, tint=0.4, dy=0))],
                     front=img_layer(step_layer), layers=[lambda im, dr, t, d, w: loose_blade(dr, 1150, 860, 130, 0, "worse", crumple=1)], cam=(1.0, 960, 540, 1.08, 1000, 600), wind=0.05)
    if sid in ("S24", "S26", "S31", "S32", "S53"):
        wmst = "patched" if sid == "S53" else "worse"
        spin = (lambda t, d: t * 900) if sid == "S53" else (lambda t, d: 6 * math.sin(t))
        blur = (lambda t, d: 0.8) if sid == "S53" else (lambda t, d: 0.0)
        milo = "milo_back"; mflip = False
        if sid in ("S31", "S32", "S53"): milo = "milo_front"
        if sid == "S32": milo, mflip = "milo_side", True
        pm = None; mm = None; wind = 0.05
        if sid == "S26": pm = lambda t, d: dict(dx=-150 * ramp(t, 2.0, 4.0))
        if sid == "S31":
            pm = breathing([(0.6, 2.6, 4.6), (4.8, 6.8, 8.6)]); mm = breathing([(0.4, 2.6, 4.6), (4.6, 6.8, 8.6)])
            wind = lambda t, d: 0.25 * (1 - ramp(t, 0, 4))
        if sid == "S53": pm = lambda t, d: dict(rot=-3); mm = lambda t, d: dict(rot=3)
        px, mx = (620, 1300) if sid != "S53" else (800, 1120)
        sc = Scene(porch, back=gb, chars=[Char("pip_front", px, 1120, 540, who=P, motion=pm),
                                          Char(milo, mx, 1110, 450, flip=mflip, who=M, motion=mm)], front=img_layer(step_layer),
                   layers=[layer_windmill(1560, 330, 110, wmst, ang=spin, blur=blur, stick_len=1.3)], wind=wind,
                   cam={"S24": None, "S26": None, "S31": (1.0, 960, 540, 1.08, 960, 580), "S32": (1.0, 960, 540, 1.08, 960, 600), "S53": (1.0, 960, 540, 1.1, 960, 560)}[sid])
        if sid == "S31":
            sc.post = lambda im, t, d: Image.blend(im, Image.new("RGB", (W, H), (255, 200, 130)), 0.08 * ramp(t, 1, 7))
        return sc
    if sid == "S25":
        return Scene(porch, back=gb, chars=[Char("milo_worried", 960, 1260, 900, who=M, motion=lambda t, d: dict(rot=5 * math.sin(t * 5) if t < 2.5 else 0, tint=0.3))], wind=0.05)
    if sid == "S27":
        return Scene(porch, back=gb, chars=[Char("pip_worried", 640, 1080, 460, who=P), Char("milo_back", 1450, 1350, 980, who=M, z=2)], front=None,
                     layers=[layer_windmill(1560, 330, 110, "worse", ang=lambda t, d: 6, stick_len=1.3)], wind=0.08, cam=(1.0, 960, 540, 1.15, 760, 600))
    if sid in ("S29", "S30", "S33", "S35", "S36", "S37", "S41"):
        mm = None; lays = [layer_windmill(1560, 330, 110, "worse", ang=lambda t, d: 6, stick_len=1.3)]
        if sid == "S29": mm = lambda t, d: dict(rot=-6 * (1 - ramp(t, 3, 5)))
        if sid == "S30":
            mm = breathing([(3.3, 5.2, 7.9)]); lays.append(cap("TAKE A BREATH", ["BREATH"], 3.0, 6.2))
        if sid == "S33": lays.append(lambda im, dr, t, d, w: thought(dr, 1180, 230, t, 0.4))
        if sid == "S36": mm = lambda t, d: dict(sx=1 + 0.08 * (ramp(t, 1.2, 2.2) - ramp(t, 3.6, 5)), tint=0.5 * (ramp(t, 1.2, 2.2) - ramp(t, 3.6, 5)))
        if sid == "S37": lays.append(lambda im, dr, t, d, w: loose_blade(dr, 1270, 700 - 30 * ramp(t, 0.5, 1.5), 210, 250, "worse"))
        if sid == "S41": mm = lambda t, d: dict(rot=7 * ramp(t, 0.8, 1.6))
        return Scene(porch, back=gb, chars=[Char("milo_front", 900, 1150, 760, who=M, motion=mm)], layers=lays, wind=0.04)
    if sid == "S34":
        return Scene(porch, back=gb, chars=[Char("pip_front", 640, 1120, 540, who=P, motion=lambda t, d: dict(rot=-5 * ramp(t, 3.5, 4.2) + 5 * ramp(t, 4.6, 5.2))),
                                            Char("milo_side", 1300, 1110, 450, flip=True, who=M, motion=lambda t, d: dict(dx=-320 * ramp(t, 0.3, 2.0), dy=-abs(math.sin(t * 6)) * 10 * (t < 2)))],
                     front=img_layer(step_layer), layers=[layer_windmill(1560, 330, 110, "worse", ang=lambda t, d: 6, stick_len=1.3)], wind=0.04)
    if sid == "S38":
        return Scene(porch, back=gb, chars=[Char("pip_happy", 960, 1200, 880, who=P)], wind=0.04)
    if sid == "S39":
        return Scene(porch, back=gb, chars=[Char("pip_happy", 640, 1230, 820, who=P, motion=hop(10, 2.5, 3.3, 5)),
                                            Char("milo_surprised", 1280, 1180, 560, who=M, motion=hop(12, 2.5, 3.3, 5))], wind=0.04)
    if sid == "S40":
        return Scene(porch, back=gb, chars=two_shot("pip_front", "milo_side", py=1120, my=1110, ph=540, mh=450, px=700, mx=1150), front=img_layer(step_layer),
                     cam=(1.0, 960, 540, 1.12, 940, 560), wind=0.04)
    if sid == "S42":
        pm = lambda t, d: dict(pose="pip_worried" if t < 1.8 else "pip_happy", dy=-25 * (ramp(t, 1.8, 2.1) - ramp(t, 2.1, 2.5)), dx=170 * ramp(t, 3.3, 4.0))
        mm = lambda t, d: dict(dx=-60 * ramp(t, 3.3, 4.0), rot=-4 * ramp(t, 3.3, 4.0))
        return Scene(porch, back=gb, chars=[Char("pip_front", 700, 1120, 540, who=P, motion=pm, z=1), Char("milo_side", 1150, 1110, 450, flip=True, who=M, motion=mm)],
                     front=img_layer(step_layer), wind=0.04)
    if sid == "S43":
        return Scene(porch, back=gb, chars=two_shot("pip_front", "milo_front", mm=lambda t, d: dict(rot=6 * (ramp(t, 4.4, 4.8) - ramp(t, 5.0, 5.4))), px=680, mx=1240),
                     layers=[layer_windmill(820, 560, 120, "worse", ang=lambda t, d: 10, stick_len=3.3)], wind=0.04)
    if sid == "S44":
        def scrap(im, dr, t, d, w):
            y = lerp(830, 640, ramp(t, 0.6, 1.6)); x = 960
            for i, c in enumerate([(235, 85, 90), (255, 170, 70), (255, 220, 80), (110, 190, 95), (80, 145, 235), (160, 110, 210)]):
                dr.rectangle((x - 70, y - 50 + i * 17, x + 70, y - 33 + i * 17), fill=c)
            dr.rectangle((x - 70, y - 50, x + 70, y + 52), outline=(255, 255, 255), width=4)
            dr.rounded_rectangle((800, 820, 1120, 900), radius=10, fill=(230, 180, 120), outline=(180, 130, 80), width=4)
            if t > 1.6: [sparkle(dr, 960 + 110 * math.cos(k + t), 640 + 70 * math.sin(k * 2 + t), 18, 220) for k in range(4)]
        return Scene(bg_porch(table=True), back=gb, chars=[Char("pip_front", 740, 1000, 520, who=P), Char("milo_front", 1190, 990, 450, who=M, motion=hop(25, 2.5, 3.0, 3.8))],
                     layers=[scrap], cam=(1.0, 960, 540, 1.1, 960, 640), wind=0.04)
    if sid in ("S45", "S46"):
        def tbl(im, dr, t, d, w):
            dr.rectangle((0, 560, W, H), fill=(205, 150, 98))
            dr.ellipse((-200, 520, 2120, 1300), fill=(195, 140, 88))
            st = "worse" if sid == "S45" else "patched"
            if sid == "S45": loose_blade(dr, 760, 420, 560, 30, "torn")
            else:
                p = ramp(t, 0.8, 4.0)
                loose_blade(dr, 760, 420, 560, 30, "torn")
                if p > 0:
                    # the patch slides in and settles over the rip
                    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
                    draw_blade(ld, 760, 420, 560, math.radians(30), (0, 0, 0, 0), "patched")
                    off = int((1 - p) * 500)
                    im.paste(L, (off, -off // 3), L)
            for sx, c in ((-1, (190, 170, 230)), (1, (190, 170, 230))):  # Pip's paws hold the blade
                dr.ellipse((960 + sx * 520 - 80, 760, 960 + sx * 520 + 80, 900), fill=c, outline=(150, 130, 190), width=3)
            if sid == "S45":
                for k in range(2):
                    y = 520 + 60 * abs(math.sin(t * 2.4 + k))
                    dr.ellipse((900 + k * 160 - 80, y - 60, 900 + k * 160 + 80, y + 60), fill=(250, 215, 80), outline=(200, 160, 50), width=3)
            elif t > 4.6:
                [sparkle(dr, 1000 + 80 * math.cos(k * 2), 600 + 60 * math.sin(k * 3), 24 * abs(math.sin(t * 3 + k)), 240) for k in range(4)]
        return Scene(porch, layers=[tbl])
    if sid == "S47":
        return Scene(porch, back=gb, chars=two_shot("pip_happy", "milo_front", px=680, mx=1240),
                     layers=[layer_windmill(960, lambda t, d: lerp(700, 520, ramp(t, 0.3, 1.6)), 140, "patched", ang=lambda t, d: 8 * math.sin(t), stick_len=2.0),
                             lambda im, dr, t, d, w: [sparkle(dr, 990 + 50 * k, 560 - 30 * k, 22 * abs(math.sin(t * 3 + k)), 240) for k in range(3)] if t > 1.2 else None], wind=0.05)
    if sid == "S48":
        return Scene(porch, back=gb, chars=[Char("pip_front", 1250, 1010, 500, who=P, motion=lambda t, d: dict(dx=-300 * ramp(t, 2.0, 3.5))),
                                            Char("milo_front", 1460, 1000, 400, who=M, motion=lambda t, d: dict(dx=-300 * ramp(t, 2.2, 3.7)))],
                     layers=[layer_windmill(1560, lambda t, d: lerp(560, 330, ramp(t, 0.3, 1.6)), 110, "patched", ang=lambda t, d: 6 * math.sin(t), stick_len=1.3)],
                     wind=lambda t, d: 0.7 * ramp(t, 3.0, 6.0))
    if sid == "S49":
        spin = lambda t, d: (t - 1.2) ** 2 * 120 if t > 1.2 else 0
        return Scene(porch, back=gb, chars=[Char("pip_front", 600, 1010, 500, who=P, motion=lambda t, d: dict(rot=4 * math.sin(t * 8))),
                                            Char("milo_side", 1020, 1000, 410, flip=True, who=M, motion=lambda t, d: dict(dx=-260 * ramp(t, 0.8, 2.0)))],
                     layers=[layer_windmill(1560, 300, 200, "patched", ang=spin, blur=lambda t, d: 0.5 * ramp(t, 4, 7), stick_len=1.0), layer_wind(4)],
                     wind=lambda t, d: 1.0 if t < 4 else 0.8)
    if sid == "S50":
        return Scene(porch, back=gb, layers=[layer_windmill(960, 470, 340, "patched", ang=lambda t, d: 300 + t * 900, blur=lambda t, d: 0.4 + 0.5 * ramp(t, 0, 3), stick_len=2.0),
                                             lambda im, dr, t, d, w: [sparkle(dr, 960 + 420 * math.cos(k * 1.3 + t), 470 + 380 * math.sin(k * 1.7 + t), 26 * abs(math.sin(t * 2 + k)), 230) for k in range(7)],
                                             layer_wind(5)], wind=0.6, cam=(1.0, 960, 540, 1.1, 960, 500))
    if sid == "S51":
        return Scene(porch, back=gb, chars=[Char("pip_happy", 640, 1230, 820, who=P, motion=lambda t, d: dict(rot=4 * math.sin(t * 9))),
                                            Char("milo_happy", 1280, 1180, 560, who=M, motion=hop(30, 2.4))],
                     layers=[layer_windmill(960, 260, 110, "patched", ang=lambda t, d: t * 900, blur=lambda t, d: 0.8, stick_len=1.0), layer_wind(6)], wind=0.5)
    if sid == "S52":
        def scarf(im, dr, t, d, w):
            if t < 0.9: return
            p = ramp(t, 0.9, 1.6); q = ramp(t, 4.6, 5.4)
            x = lerp(760, 1180, p) - 380 * q; y = lerp(560, 640, p) + 120 * q
            pts = [(x - 120, y - 40), (x + 120, y - 60 + 15 * math.sin(t * 9)), (x + 110, y + 60), (x - 110, y + 70 + 15 * math.sin(t * 8))]
            dr.polygon(pts, fill=(150, 185, 120), outline=(110, 145, 85))
            for k in range(5): dr.line((x - 100 + k * 50, y - 45, x - 95 + k * 50, y + 60), fill=(130, 165, 100), width=4)
        return Scene(porch, back=gb, chars=[Char("pip_happy", 700, 1010, 520, who=P, motion=hop(10, 2.5, 3.0, 6)),
                                            Char("milo_front", 1180, 1000, 430, who=M, motion=lambda t, d: dict(rot=6 * math.sin(t * 10) if 1.6 < t < 4.6 else 0))],
                     layers=[scarf, layer_windmill(1560, 330, 110, "patched", ang=lambda t, d: t * 700, blur=lambda t, d: 0.7, stick_len=1.3), layer_wind(7)],
                     wind=lambda t, d: 0.6 * (1 - ramp(t, 1.5, 3.5)))
    if sid == "S54":
        sc = Scene(porch, back=gb, chars=[Char("pip_happy", 760, 1010, 430, who=P, motion=lambda t, d: dict(rot=6 * math.sin(t * 4))),
                                          Char("milo_front", 1100, 1000, 350, who=M, motion=lambda t, d: dict(rot=6 * math.sin(t * 4 + 1)))],
                   layers=[layer_windmill(1560, 330, 110, "patched", ang=lambda t, d: t * 700, blur=lambda t, d: 0.7, stick_len=1.3),
                           cap("PAUSE. BREATHE. TELL ME.", ["BREATHE"], 0.8, 6.0, "mid")], wind=0.15, cam=(1.12, 960, 600, 1.0, 960, 540))
        sc.post = lambda im, t, d: Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), ramp(t, 5.0, 6.0))
        return sc
    raise ValueError(sid)

def drawing(d, x, y, s, rot=0):
    w, h = 220 * s, 170 * s
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=10, fill=(255, 255, 250), outline=(200, 190, 175), width=3)
    windmill(d, x, y - 10 * s, 55 * s, 20 + rot, "full", 4, True, 0, 1.2)

def wing_pat(d, x, y, t):
    yy = y + 25 * abs(math.sin(t * 3))
    d.ellipse((x - 70, yy - 50, x + 70, yy + 50), fill=(250, 215, 80), outline=(200, 160, 50), width=3)

def paws(d, x, y):
    for sx in (-1, 1):
        d.ellipse((x + sx * 60 - 55, y - 35, x + sx * 60 + 55, y + 35), fill=(195, 175, 232), outline=(150, 130, 190), width=3)

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
    final = os.path.join(HERE, "..", "ep2_milo_and_the_windy_day.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", "360", "-movflags", "+faststart", final], check=True)
    print("final", final)

if __name__ == "__main__":
    main()
