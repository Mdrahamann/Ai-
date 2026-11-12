"""Episode 4: Counting 1 to 10 with Milo & Pip (learning video + 2 vertical Shorts + thumbnail).

One script builds everything from a single timeline:
  python3 make.py timeline   -> voices (Kokoro TTS) + out/timeline.json
  python3 make.py audio      -> out/mix.wav, ../ep4_captions.srt, shorts audio
  python3 make.py video      -> ../ep4_counting_1_to_10.mp4 (1920x1080)
  python3 make.py shorts     -> ../shorts/*.mp4 (1080x1920)
  python3 make.py thumb      -> ../thumbnail_ep4.png (1280x720)
KOKORO_DIR must hold kokoro-v1.0.int8.onnx and voices-v1.0.bin (timeline step only).
"""
import os, sys, re, json, math, subprocess, tempfile, functools
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
EP = os.path.join(HERE, "..")
CUT = os.path.join(HERE, "..", "..", "ep1", "build", "cutouts")
FONT = os.path.join(HERE, "..", "..", "ep1", "build", "fonts", "Fredoka.ttf")
FPS = 24
SR = 48000
BEAT = 60 / 110          # music tempo; counts land on beats

WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
THINGS = {1: ("sun", "One big sun!"), 2: ("butterfly", "Two butterflies!"), 3: ("star", "Three shiny stars!"),
          4: ("apple", "Four red apples!"), 5: ("duck", "Five little ducks!"), 6: ("flower", "Six pretty flowers!"),
          7: ("balloon", "Seven balloons!"), 8: ("fish", "Eight little fish!"), 9: ("cookie", "Nine star cookies!"),
          10: ("bubble", "Ten bubbles! Pop!")}
NUMCOL = [(0, 0, 0), (235, 80, 90), (245, 145, 50), (235, 185, 30), (90, 175, 85), (60, 150, 225),
          (150, 100, 210), (235, 90, 160), (40, 170, 170), (220, 120, 60), (110, 120, 230)]
BGCOL = {1: ((150, 210, 250), (215, 240, 255)), 2: ((200, 235, 200), (240, 252, 230)), 3: ((70, 80, 160), (140, 120, 200)),
         4: ((255, 225, 200), (255, 245, 230)), 5: ((140, 205, 245), (190, 230, 250)), 6: ((215, 240, 200), (250, 250, 225)),
         7: ((160, 215, 250), (225, 245, 255)), 8: ((60, 150, 210), (120, 200, 235)), 9: ((205, 230, 246), (186, 214, 238)),
         10: ((180, 225, 250), (235, 248, 255))}
GROUND = {1: (150, 210, 120), 2: (150, 210, 120), 3: (90, 90, 150), 4: (200, 160, 110), 5: (110, 170, 220), 6: (150, 210, 120),
          7: (150, 210, 120), 8: (230, 210, 160), 9: (215, 160, 100), 10: (150, 210, 120)}

# ------------------------------------------------------------------ timeline
def build_timeline(dur_of):
    """dur_of(who, text) -> seconds. Returns events: segments + voice lines + sfx + visual cues."""
    ev = dict(lines=[], sfx=[], segs=[], counts=[])
    t = 0.0
    def say(who, text, at):
        d = dur_of(who, text); ev["lines"].append(dict(who=who, text=text, start=round(at, 3), end=round(at + d, 3))); return at + d
    def q(x): return math.ceil(x / BEAT - 1e-6) * BEAT   # snap to next beat
    # intro
    s0 = t
    e = say("Milo", "Hi friends! Let's count to ten!", t + 0.5)
    e = say("Pip", "Count with us!", e + 0.3)
    ev["sfx"] += [("sparkle", t + 0.2), ("boing", e + 0.1)]
    t = q(e + 1.2); ev["segs"].append(dict(kind="intro", start=s0, end=t))
    # numbers
    for n in range(1, 11):
        s0 = t; caller = "Milo" if n % 2 else "Pip"; other = "Pip" if n % 2 else "Milo"
        ev["sfx"].append(("ding", t + 0.1))
        e = say(caller, f"Number {WORDS[n].lower()}!", t + 0.25)
        c = q(e + 0.5); objs = []
        for i in range(1, n + 1):
            say(caller if i % 2 else other, WORDS[i] + "!", c)
            ev["sfx"].append(("pop", c)); objs.append(round(c, 3))
            c += 2 * BEAT if n <= 5 else 1.5 * BEAT
        e = say(caller, THINGS[n][1], c + 0.2)
        ev["sfx"].append(("chime", c + 0.1))
        p = e + 0.4
        e = say(other, f"Say it with me... {WORDS[n].lower()}!", p)
        rep = e + 0.15
        t = q(rep + 1.6)   # pause so children can say it too
        ev["segs"].append(dict(kind="number", n=n, start=round(s0, 3), end=round(t, 3), objs=objs, phrase=round(c + 0.1, 3), repeat=round(rep, 3)))
    # recap: count up fast with the number strip
    s0 = t
    e = say("Pip", "Now let's count them all!", t + 0.3)
    c = q(e + 0.4); marks = []
    for i in range(1, 11):
        say("Milo" if i % 2 else "Pip", WORDS[i] + "!", c); ev["sfx"].append(("ting", c)); marks.append(round(c, 3)); c += 2 * BEAT
    e = say("Milo", "Great counting!", c + 0.2); ev["sfx"].append(("bigchime", c + 0.1))
    t = q(e + 1.0); ev["segs"].append(dict(kind="recap", start=round(s0, 3), end=round(t, 3), marks=marks))
    # blast off: count down 10 to 1
    s0 = t
    e = say("Pip", "Now count down. Ready for blast off?", t + 0.3)
    c = q(e + 0.5); marks = []
    for i in range(10, 0, -1):
        say("Milo" if i % 2 else "Pip", WORDS[i] + "!", c); ev["sfx"].append(("tick", c)); marks.append(round(c, 3)); c += 2 * BEAT
    e = say("Milo", "Blast off!", c); ev["sfx"] += [("rocket", c), ("bigchime", c + 1.2)]
    t = q(e + 3.5); ev["segs"].append(dict(kind="blastoff", start=round(s0, 3), end=round(t, 3), marks=marks, launch=round(c, 3)))
    # goodbye + end screen
    s0 = t
    e = say("Pip", "You counted to ten. Hooray!", t + 0.3)
    e = say("Milo", "Bye-bye, friends! See you next time!", e + 0.3)
    t = round(e + 1.5, 3); ev["segs"].append(dict(kind="bye", start=s0, end=t))
    ev["segs"].append(dict(kind="end", start=t, end=t + 12.0)); t += 12.0
    ev["total"] = round(t, 3)
    return ev

# ------------------------------------------------------------------ voices
VOICES = {"Milo": ("af_sky", 0.85, 3.0), "Pip": ("af_heart", 0.85, 1.0)}
_k = None
def voice_clip(who, text):
    import soundfile as sf
    cache = os.path.join(OUT, "tts_cache"); os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, re.sub(r"[^a-z0-9]+", "_", f"{who}_{text}".lower())[:90] + ".wav")
    if os.path.exists(p): return sf.read(p, dtype="float32")[0]
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        kd = os.environ["KOKORO_DIR"]; _k = Kokoro(os.path.join(kd, "kokoro-v1.0.int8.onnx"), os.path.join(kd, "voices-v1.0.bin"))
    v, sp, ps = VOICES[who]
    a, sr = _k.create(text, voice=v, speed=sp, lang="en-us")
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav"); sf.write(i, a, sr); r = 2 ** (ps / 12)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-af", f"asetrate={int(sr * r)},aresample={SR},atempo={1 / r:.5f}", o], check=True)
        a = sf.read(o, dtype="float32")[0]
    # trim leading/trailing silence so counts land exactly on the beat
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz): a = a[max(0, nz[0] - 200): nz[-1] + 1200]
    a = (a / (np.abs(a).max() + 1e-9) * 0.85).astype(np.float32)
    sf.write(p, a, SR); return a

def timeline():
    ev = build_timeline(lambda w, t: len(voice_clip(w, t)) / SR)
    json.dump(ev, open(os.path.join(OUT, "timeline.json"), "w"), indent=1)
    print("total", ev["total"], "s")

def load_tl(): return json.load(open(os.path.join(OUT, "timeline.json")))

# ------------------------------------------------------------------ audio
def audio():
    import soundfile as sf
    sys.path.insert(0, HERE); from synth import SFX, bell, nt, sweep, env_ad, smooth, noise, T, music_section, pluck
    ev = load_tl(); N = int((ev["total"] + 0.5) * SR)
    def place(buf, clip, t, g=1.0):
        i = int(t * SR); j = min(len(buf), i + len(clip))
        if 0 <= i < len(buf): buf[i:j] += clip[: j - i] * g
    dlg = np.zeros(N, np.float32)
    for L in ev["lines"]: place(dlg, voice_clip(L["who"], L["text"]), L["start"])
    fx = dict(SFX)
    def _pop():
        a = 0.2 * bell(nt(91), 0.3, 8); a[: int(0.09 * SR)] += 0.5 * sweep(500, 1400, 0.09) * env_ad(0.09, 0.002, 4); return a
    fx["pop"] = _pop
    fx["ding"] = lambda: 0.5 * bell(nt(84), 1.2, 4)
    fx["tick"] = lambda: 0.4 * bell(nt(96), 0.15, 9)
    fx["rocket"] = lambda: 0.9 * smooth(noise(3.0), 12) * np.minimum(1, T(3.0) / 0.2) * np.exp(-T(3.0) * 0.8) + 0.3 * sweep(80, 400, 3.0) * np.exp(-T(3.0) * 0.6)
    sfx = np.zeros(N, np.float32)
    for name, at in ev["sfx"]: place(sfx, fx[name]().astype(np.float32), at)
    # music: one bouncy bed at the counting tempo, a soft change for the end screen
    mus = np.zeros(N, np.float32)
    end_start = next(s["start"] for s in ev["segs"] if s["kind"] == "end")
    bed = music_section(end_start + 1, "travel", seed=4)  # 120-bpm bouncy bed
    place(mus, bed.astype(np.float32), 0)
    out = music_section(13, "outro", seed=5); fade = np.clip((13 - np.arange(len(out)) / SR) / 3, 0, 1); place(mus, (out * fade).astype(np.float32), end_start)
    von = np.clip(smooth(np.clip(smooth((np.abs(dlg) > 0.02).astype(np.float32), int(0.2 * SR)) * 8, 0, 1), int(0.25 * SR)), 0, 1)
    mus *= (1 - 0.5 * von)
    norm = lambda x, p: x / (np.abs(x).max() + 1e-9) * p
    mix = dlg * 0.9 + norm(mus, 0.32) + norm(sfx, 0.45)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    sf.write(os.path.join(OUT, "mix_raw.wav"), np.stack([mix, mix], 1), SR)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(OUT, "mix_raw.wav"), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR),
                    os.path.join(OUT, "mix.wav")], check=True)
    def fmt(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    with open(os.path.join(EP, "ep4_captions.srt"), "w") as f:
        for i, L in enumerate(ev["lines"], 1): f.write(f"{i}\n{fmt(L['start'])} --> {fmt(L['end'])}\n{L['text']}\n\n")
    print("audio done", ev["total"])

# ------------------------------------------------------------------ drawing
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def pop_scale(p):  # 0 -> overshoot -> 1
    if p <= 0: return 0.0
    if p >= 1: return 1.0
    return math.sin(p * math.pi * 0.75) / math.sin(math.pi * 0.75) * (1 + 0.25 * math.sin(p * math.pi))

@functools.lru_cache(None)
def font(size, w="Bold"):
    f = ImageFont.truetype(FONT, size); f.set_variation_by_name(w); return f

@functools.lru_cache(None)
def sprite(pose, h, flip=False):
    im = Image.open(os.path.join(CUT, pose + ".png")).convert("RGBA")
    im = im.resize((max(1, round(im.width * h / im.height)), int(h)), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im

@functools.lru_cache(None)
def background(n, W, H):
    top, low = BGCOL.get(n, ((255, 236, 200), (255, 248, 230)))
    a = np.linspace(0, 1, H)[:, None, None]
    img = (np.array(top) * (1 - a) + np.array(low) * a).astype(np.uint8)
    im = Image.fromarray(np.repeat(img, W, 1), "RGB"); d = ImageDraw.Draw(im)
    g = GROUND.get(n, (150, 210, 120)); gy = int(H * 0.84)
    d.ellipse((-W * 0.2, gy - H * 0.05, W * 0.7, gy + H * 0.4), fill=tuple(min(255, c + 15) for c in g))
    d.ellipse((W * 0.35, gy - H * 0.035, W * 1.2, gy + H * 0.4), fill=g)
    d.rectangle((0, gy + H * 0.04, W, H), fill=g)
    rs = np.random.default_rng(n)
    if n == 3:  # night sky dots
        for _ in range(60):
            x, y = rs.uniform(0, W), rs.uniform(0, H * 0.7); d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 230))
    elif n not in (8,):
        for k in range(3):
            cx, cy, s = rs.uniform(0.05, 0.95) * W, rs.uniform(0.06, 0.3) * H, rs.uniform(0.035, 0.06) * W
            for dx, dy, r in [(-1, .1, .55), (-.3, -.25, .75), (.45, -.1, .65), (1, .2, .5), (0, .25, .7)]:
                d.ellipse((cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s), fill=(255, 255, 255))
    if n == 8:  # bubbles in water
        for _ in range(25):
            x, y, r = rs.uniform(0, W), rs.uniform(0, H * 0.8), rs.uniform(4, 12); d.ellipse((x - r, y - r, x + r, y + r), outline=(220, 240, 255), width=2)
    return im

def draw_thing(d, kind, x, y, s, t=0.0, i=0):
    """s = size in px (bounding box ~ s)."""
    r = s / 2
    if kind == "sun":
        for k in range(12):
            a = k * math.pi / 6 + t * 0.6
            d.line((x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75, x + math.cos(a) * r * 1.05, y + math.sin(a) * r * 1.05), fill=(255, 190, 40), width=max(3, int(s * 0.05)))
        d.ellipse((x - r * 0.65, y - r * 0.65, x + r * 0.65, y + r * 0.65), fill=(255, 215, 60), outline=(240, 170, 30), width=max(2, int(s * 0.02)))
        face(d, x, y, r * 0.65)
    elif kind == "butterfly":
        f = 0.6 + 0.4 * abs(math.sin(t * 6 + i))
        c1, c2 = [(240, 120, 170), (250, 180, 80)][i % 2], [(250, 190, 210), (255, 220, 140)][i % 2]
        for sx in (-1, 1):
            d.ellipse((x + sx * r * 0.05 - (r * 0.85 * f if sx < 0 else 0), y - r * 0.8, x + sx * r * 0.05 + (r * 0.85 * f if sx > 0 else 0), y + r * 0.05), fill=c1, outline=(90, 60, 70), width=2)
            d.ellipse((x + sx * r * 0.05 - (r * 0.6 * f if sx < 0 else 0), y - r * 0.05, x + sx * r * 0.05 + (r * 0.6 * f if sx > 0 else 0), y + r * 0.6), fill=c2, outline=(90, 60, 70), width=2)
        d.rounded_rectangle((x - r * 0.08, y - r * 0.6, x + r * 0.08, y + r * 0.55), radius=int(r * 0.08), fill=(90, 60, 70))
    elif kind == "star":
        pts = [(x + math.cos(math.radians(-90 + k * 36)) * (r if k % 2 == 0 else r * 0.45), y + math.sin(math.radians(-90 + k * 36)) * (r if k % 2 == 0 else r * 0.45)) for k in range(10)]
        d.polygon(pts, fill=(255, 220, 70), outline=(235, 170, 40), width=max(2, int(s * 0.03))); face(d, x, y + r * 0.05, r * 0.45)
    elif kind == "apple":
        d.ellipse((x - r * 0.8, y - r * 0.6, x + r * 0.1, y + r * 0.8), fill=(225, 55, 60)); d.ellipse((x - r * 0.1, y - r * 0.6, x + r * 0.8, y + r * 0.8), fill=(225, 55, 60))
        d.line((x, y - r * 0.55, x + r * 0.1, y - r * 0.95), fill=(120, 80, 40), width=max(3, int(s * 0.05)))
        d.ellipse((x + r * 0.1, y - r * 0.95, x + r * 0.55, y - r * 0.7), fill=(90, 175, 80)); d.ellipse((x - r * 0.5, y - r * 0.35, x - r * 0.25, y - r * 0.05), fill=(255, 150, 150))
    elif kind == "duck":
        d.ellipse((x - r * 0.85, y - r * 0.1, x + r * 0.7, y + r * 0.75), fill=(255, 215, 60), outline=(230, 170, 40), width=2)
        d.ellipse((x - r * 0.05, y - r * 0.75, x + r * 0.7, y + r * 0.05), fill=(255, 215, 60), outline=(230, 170, 40), width=2)
        d.polygon([(x + r * 0.62, y - r * 0.4), (x + r * 1.0, y - r * 0.3), (x + r * 0.62, y - r * 0.18)], fill=(250, 140, 40))
        d.ellipse((x + r * 0.3, y - r * 0.55, x + r * 0.45, y - r * 0.4), fill=(30, 30, 30))
    elif kind == "flower":
        cols = [(240, 110, 150), (160, 120, 230), (250, 160, 60), (90, 160, 240), (240, 90, 90), (250, 200, 60)]
        d.line((x, y, x, y + r * 1.0), fill=(80, 160, 70), width=max(3, int(s * 0.05)))
        for k in range(6):
            a = k * math.pi / 3 + t * 0.4
            d.ellipse((x + math.cos(a) * r * 0.42 - r * 0.32, y + math.sin(a) * r * 0.42 - r * 0.32, x + math.cos(a) * r * 0.42 + r * 0.32, y + math.sin(a) * r * 0.42 + r * 0.32), fill=cols[i % 6])
        d.ellipse((x - r * 0.25, y - r * 0.25, x + r * 0.25, y + r * 0.25), fill=(255, 220, 80))
    elif kind == "balloon":
        cols = [(235, 80, 90), (245, 145, 50), (235, 200, 40), (90, 175, 85), (60, 150, 225), (150, 100, 210), (235, 90, 160)]
        yy = y + math.sin(t * 2 + i) * r * 0.08
        d.line((x, yy + r * 0.7, x + math.sin(t * 2 + i) * r * 0.15, yy + r * 1.4), fill=(120, 120, 120), width=2)
        d.ellipse((x - r * 0.55, yy - r * 0.8, x + r * 0.55, yy + r * 0.7), fill=cols[i % 7]); d.ellipse((x - r * 0.3, yy - r * 0.55, x - r * 0.1, yy - r * 0.25), fill=(255, 255, 255))
    elif kind == "fish":
        cols = [(250, 140, 60), (240, 90, 120), (250, 200, 60), (120, 200, 120)]
        xx = x + math.sin(t * 1.5 + i) * r * 0.15
        d.polygon([(xx - r * 0.55, y), (xx - r * 1.0, y - r * 0.35), (xx - r * 1.0, y + r * 0.35)], fill=cols[i % 4])
        d.ellipse((xx - r * 0.7, y - r * 0.45, xx + r * 0.7, y + r * 0.45), fill=cols[i % 4]); d.ellipse((xx + r * 0.3, y - r * 0.15, xx + r * 0.45, y), fill=(30, 30, 30))
    elif kind == "cookie":
        pts = [(x + math.cos(math.radians(-90 + k * 36)) * (r if k % 2 == 0 else r * 0.5), y + math.sin(math.radians(-90 + k * 36)) * (r if k % 2 == 0 else r * 0.5)) for k in range(10)]
        d.polygon(pts, fill=(235, 180, 90), outline=(200, 130, 60), width=max(2, int(s * 0.03))); d.ellipse((x - r * 0.25, y - r * 0.25, x + r * 0.25, y + r * 0.25), fill=(255, 236, 120))
    elif kind == "bubble":
        hue = [(120, 190, 255), (200, 150, 255), (255, 160, 200), (130, 220, 200)][i % 4]
        d.ellipse((x - r * 0.75, y - r * 0.75, x + r * 0.75, y + r * 0.75), fill=hue + (150,), outline=(70, 130, 210), width=max(3, int(s * 0.05)))
        d.arc((x - r * 0.55, y - r * 0.55, x + r * 0.45, y + r * 0.45), 200, 260, fill=(255, 255, 255), width=max(3, int(s * 0.05)))

def face(d, x, y, r):
    d.ellipse((x - r * 0.38, y - r * 0.25, x - r * 0.18, y + r * 0.0), fill=(60, 40, 30)); d.ellipse((x + r * 0.18, y - r * 0.25, x + r * 0.38, y), fill=(60, 40, 30))
    d.arc((x - r * 0.35, y - r * 0.15, x + r * 0.35, y + r * 0.45), 20, 160, fill=(60, 40, 30), width=max(2, int(r * 0.1)))

def big_text(im, text, cx, cy, size, col, scale=1.0, stroke=None):
    if scale <= 0.01: return
    f = font(max(8, int(size * scale)))
    d = ImageDraw.Draw(im)
    sw = stroke if stroke is not None else max(4, int(size * scale * 0.08))
    d.text((cx, cy), text, font=f, fill=col, anchor="mm", stroke_width=sw, stroke_fill=(255, 255, 255))

def sparkle(d, x, y, r, a=255):
    d.polygon([(x, y - r), (x + r * .22, y - r * .22), (x + r, y), (x + r * .22, y + r * .22), (x, y + r), (x - r * .22, y + r * .22), (x - r, y), (x - r * .22, y - r * .22)], fill=(255, 255, 255, int(a)))

# ------------------------------------------------------------------ frame
def talking(ev, who, t):
    return any(L["who"] == who and L["start"] <= t <= L["end"] for L in ev["lines"])

def chars(im, ev, t, W, H, n, celebrate=False):
    vert = H > W
    h = int(H * (0.24 if vert else 0.36))
    base = int(H * (0.97 if vert else 0.98))
    for who, pose, x in (("Milo", "milo_front", W * (0.16 if vert else 0.11)), ("Pip", "pip_happy", W * (0.84 if vert else 0.89))):
        hh = h * (0.92 if who == "Milo" else 1.08)
        dy = 0; sy = 1
        if talking(ev, who, t):
            ph = (t * 4.2) % 1; dy -= abs(math.sin(math.pi * ph)) * hh * 0.03; sy = 1 + 0.025 * math.sin(2 * math.pi * ph)
        else:
            sy = 1 + 0.01 * math.sin(t * 3 + (0 if who == "Milo" else 1))
        if celebrate: dy -= abs(math.sin(t * 7)) * hh * 0.12
        sp = sprite(pose, int(hh))
        if sy != 1: sp = sp.resize((sp.width, max(1, int(sp.height * sy))), Image.BILINEAR)
        im.paste(sp, (int(x - sp.width / 2), int(base + dy - sp.height)), sp)

def layout(n, W, H):
    """centers for n objects inside the content box"""
    vert = H > W
    top, bot = (0.30, 0.74) if vert else (0.38, 0.81)
    left, right = (0.08, 0.92) if vert else (0.17, 0.83)
    per = (3 if n <= 6 else 4) if vert else (n if n <= 5 else 5)
    rows = math.ceil(n / per)
    cw = (right - left) * W / per; ch = (bot - top) * H / max(rows, 1)
    size = min(cw, ch) * 0.78
    size = min(size, (W * 0.26) if vert else (H * 0.26))
    pts = []
    for i in range(n):
        r_, c_ = divmod(i, per); in_row = min(per, n - r_ * per)
        x = W / 2 + (c_ - (in_row - 1) / 2) * cw
        y = top * H + (r_ + 0.5) * ch
        pts.append((x, y))
    return pts, size

def frame(ev, t, W, H):
    seg = next((s for s in ev["segs"] if s["start"] <= t < s["end"]), ev["segs"][-1])
    k = seg["kind"]; lt = t - seg["start"]
    if k == "number": n = seg["n"]
    else: n = {"intro": 7, "recap": 10, "blastoff": 3, "bye": 7, "end": 7}[k]
    im = background(n, W, H).copy(); d = ImageDraw.Draw(im, "RGBA")
    vert = H > W
    if k == "intro":
        for i in range(1, 11):
            p = ease((lt - 0.2 - i * 0.12) / 0.6)
            x = W * (0.12 + 0.76 * (i - 1) / 9) if not vert else W * (0.18 + 0.64 * ((i - 1) % 5) / 4)
            y0 = H * (0.42 if not vert else (0.36 if i <= 5 else 0.5))
            y = -H * 0.2 + (y0 + math.sin(t * 3 + i) * H * 0.015 + H * 0.2) * p
            big_text(im, str(i), x, y, int(H * (0.13 if not vert else 0.075)), NUMCOL[i])
        big_text(im, "COUNT TO 10!", W / 2, H * (0.18 if not vert else 0.2), int(H * (0.12 if not vert else 0.06)), (235, 110, 40), pop_scale((lt - 0.4) / 0.5))
        chars(im, ev, t, W, H, n, celebrate=lt > 2.5)
    elif k == "number":
        objs = seg["objs"]; kind = THINGS[n][0]
        sc = pop_scale(lt / 0.45)
        after = t >= seg["phrase"]
        bounce = 1 + 0.08 * math.sin((t - seg["phrase"]) * 9) * math.exp(-(t - seg["phrase"]) * 2) if after else 1
        big_text(im, str(n), W * (0.5 if vert else 0.5), H * (0.14 if vert else 0.17), int(H * (0.12 if vert else 0.2)), NUMCOL[n], sc * bounce)
        if after:
            big_text(im, WORDS[n].upper(), W / 2, H * (0.235 if vert else 0.305), int(H * (0.04 if vert else 0.07)), NUMCOL[n], pop_scale((t - seg["phrase"]) / 0.4))
        pts, size = layout(n, W, H)
        for i, (x, y) in enumerate(pts):
            if t < objs[i]: continue
            p = pop_scale((t - objs[i]) / 0.35)
            s = size * p
            draw_thing(d, kind, x, y, s, t, i)
            # the count number above each object as it is counted
            big_text(im, str(i + 1), x, y - size * 0.62, int(size * 0.28), NUMCOL[n], ease((t - objs[i]) / 0.25) * (1.25 if t - objs[i] < 0.5 else 1.0))
        if t >= seg["repeat"] and t < seg["end"]:  # "say it with me" pause: a pulsing ear icon
            pr = 1 + 0.08 * math.sin(t * 8)
            big_text(im, "Your turn!", W / 2, H * (0.79 if vert else 0.9), int(H * (0.035 if vert else 0.06)), (235, 110, 40), pr)
        chars(im, ev, t, W, H, n, celebrate=after and t < seg["repeat"])
    elif k == "recap":
        marks = seg["marks"]
        for i in range(10):
            on = t >= marks[i]
            if vert: x = W * (0.16 + 0.17 * (i % 5)); y = H * (0.36 if i < 5 else 0.5)
            else: x = W * (0.1 + 0.089 * i); y = H * 0.45
            s = 1.0 + (0.35 * math.exp(-(t - marks[i]) * 3) if on else 0)
            big_text(im, str(i + 1), x, y, int(H * (0.07 if vert else 0.12)), NUMCOL[i + 1] if on else (190, 190, 200), s)
        if t >= marks[-1] + 0.5:
            for j in range(10):
                sparkle(d, W * (0.1 + 0.08 * j), H * (0.3 + 0.1 * math.sin(t * 3 + j)), 22 * abs(math.sin(t * 4 + j)), 230)
        chars(im, ev, t, W, H, n, celebrate=t >= marks[-1])
    elif k == "blastoff":
        marks = seg["marks"]; launch = seg["launch"]
        cur = None
        for i, m in enumerate(marks):
            if t >= m: cur = 10 - i
        rx = W / 2; ry = H * (0.62 if not vert else 0.58)
        if t >= launch: ry -= (t - launch) ** 2 * H * 0.45
        if t >= launch - 0.3:
            for j in range(14):
                a = j * 0.45 + t * 4; rr = H * 0.03 * (1 + (t - launch + 0.3) * 1.5)
                d.ellipse((rx + math.sin(a) * W * 0.04 - rr, ry + H * 0.17 + j * H * 0.012 - rr, rx + math.sin(a) * W * 0.04 + rr, ry + H * 0.17 + j * H * 0.012 + rr), fill=(255, 255, 255, 170))
            d.polygon([(rx - W * 0.02, ry + H * 0.12), (rx + W * 0.02, ry + H * 0.12), (rx, ry + H * 0.2 + 15 * math.sin(t * 30))], fill=(255, 150, 40))
        rw, rh = (W * 0.06, H * 0.26) if not vert else (W * 0.12, H * 0.16)
        d.polygon([(rx - rw, ry + rh * 0.45), (rx - rw * 1.6, ry + rh * 0.55), (rx - rw, ry + rh * 0.2)], fill=(235, 80, 90))
        d.polygon([(rx + rw, ry + rh * 0.45), (rx + rw * 1.6, ry + rh * 0.55), (rx + rw, ry + rh * 0.2)], fill=(235, 80, 90))
        d.rounded_rectangle((rx - rw, ry - rh * 0.3, rx + rw, ry + rh * 0.5), radius=int(rw * 0.4), fill=(245, 245, 250), outline=(150, 150, 170), width=3)
        d.polygon([(rx - rw, ry - rh * 0.28), (rx + rw, ry - rh * 0.28), (rx, ry - rh * 0.65)], fill=(235, 80, 90))
        d.ellipse((rx - rw * 0.45, ry - rh * 0.15, rx + rw * 0.45, ry + rh * 0.05), fill=(130, 190, 240), outline=(150, 150, 170), width=3)
        if cur and t < launch:
            p = t - marks[10 - cur]
            big_text(im, str(cur), W * (0.5 if vert else 0.2), H * (0.2 if vert else 0.4), int(H * (0.12 if vert else 0.24)), NUMCOL[cur], 1 + 0.4 * math.exp(-p * 4))
        if t >= launch:
            big_text(im, "BLAST OFF!", W / 2, H * 0.2, int(H * (0.07 if vert else 0.13)), (235, 110, 40), pop_scale((t - launch) / 0.5))
            for j in range(12): sparkle(d, W * (0.08 + 0.08 * j), H * (0.12 + 0.6 * ((j * 37) % 10) / 10), 26 * abs(math.sin(t * 5 + j)), 230)
        chars(im, ev, t, W, H, n, celebrate=t >= launch)
    elif k == "bye":
        big_text(im, "GREAT JOB!", W / 2, H * 0.22, int(H * (0.07 if vert else 0.13)), (235, 110, 40), pop_scale(lt / 0.5))
        for j in range(10): sparkle(d, W * (0.1 + 0.09 * j), H * (0.35 + 0.15 * math.sin(t * 2 + j)), 24 * abs(math.sin(t * 4 + j)), 230)
        chars(im, ev, t, W, H, n, celebrate=True)
    else:  # end screen space
        im = im.filter(ImageFilter.GaussianBlur(10)); d = ImageDraw.Draw(im, "RGBA")
        for x in (0.17, 0.53):
            d.rounded_rectangle((W * x, H * 0.4, W * x + W * 0.3, H * 0.4 + W * 0.3 * 9 / 16), radius=30, fill=(255, 255, 255, 60), outline=(255, 255, 255, 180), width=5)
        d.ellipse((W / 2 - H * 0.09, H * 0.12, W / 2 + H * 0.09, H * 0.3), fill=(255, 255, 255, 60), outline=(255, 255, 255, 180), width=5)
        if t > ev["total"] - 1.0:
            im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), min(1, t - (ev["total"] - 1.0)))
    return im

# ------------------------------------------------------------------ rendering
def _render_chunk(args):
    t0, t1, W, H, path = args
    ev = load_tl()
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(int(round(t0 * FPS)), int(round(t1 * FPS))):
        p.stdin.write(frame(ev, i / FPS, W, H).convert("RGB").tobytes())
    p.stdin.close(); p.wait(); return path

def render(t0, t1, W, H, audio_path, out_path, tag):
    seg = os.path.join(OUT, f"seg_{tag}"); os.makedirs(seg, exist_ok=True)
    step = 10.0; jobs = []; t = t0; k = 0
    while t < t1 - 1e-6:
        jobs.append((t, min(t1, t + step), W, H, os.path.join(seg, f"{k:03d}.mp4"))); t += step; k += 1
    with Pool(4) as pool: paths = pool.map(_render_chunk, jobs)
    lst = os.path.join(seg, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", audio_path,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path], check=True)
    print("wrote", out_path)

def video():
    ev = load_tl()
    render(0, ev["total"], 1920, 1080, os.path.join(OUT, "mix.wav"), os.path.join(EP, "ep4_counting_1_to_10.mp4"), "main")

def shorts():
    ev = load_tl(); sd = os.path.join(EP, "shorts"); os.makedirs(sd, exist_ok=True)
    segs = ev["segs"]
    num = {s["n"]: s for s in segs if s["kind"] == "number"}
    blast = next(s for s in segs if s["kind"] == "blastoff")
    plans = [("short1_count_1_to_5.mp4", 0.0, num[5]["end"]), ("short2_count_6_to_10_blast_off.mp4", num[6]["start"], num[10]["end"]),
             ("short3_blast_off_countdown.mp4", blast["start"], blast["end"])]
    for name, a, b in plans:
        render(a, b, 1080, 1920, os.path.join(OUT, "mix.wav"), os.path.join(sd, name), name[:6])

def thumb():
    W, H = 1280, 720
    im = background(7, W, H).copy(); d = ImageDraw.Draw(im, "RGBA")
    # big numbers fan
    for i, (x, y, rot) in enumerate([(380, 300, -12), (560, 250, -4), (740, 260, 6), (900, 320, 12)]):
        L = Image.new("RGBA", (360, 360), (0, 0, 0, 0)); big_text(L, str(i + 1), 180, 180, 250, NUMCOL[i + 1], 1.0, stroke=16)
        L = L.rotate(rot, resample=Image.BICUBIC); im.paste(L, (x - 180, y - 180), L)
    for i, (x, y) in enumerate([(130, 140), (1150, 130), (1080, 300), (200, 330)]):
        draw_thing(d, ["balloon", "balloon", "star", "apple"][i], x, y, 120, 0, i + 2)
    m = sprite("milo_happy", 330); im.paste(m, (40, H - m.height + 10), m)
    p = sprite("pip_happy", 420); im.paste(p, (W - p.width - 30, H - p.height + 20), p)
    # title pill
    d.rounded_rectangle((285, 520, 995, 690), radius=60, fill=(255, 248, 235), outline=(235, 110, 40), width=8)
    big_text(im, "COUNT TO 10!", 640, 605, 100, (235, 110, 40), 1.0, stroke=6)
    im.save(os.path.join(EP, "thumbnail_ep4.png")); print("thumbnail done")

if __name__ == "__main__":
    {"timeline": timeline, "audio": audio, "video": video, "shorts": shorts, "thumb": thumb}[sys.argv[1]]()
