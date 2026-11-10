"""Episode 1 soundtrack: character voices (Kokoro TTS), synthesized music bed and sound effects.

Writes out/dialogue.wav, out/music.wav, out/sfx.wav, out/mix.wav, out/lines.json (who speaks when,
used by render.py to animate talking) and ../ep1_captions.srt.
Needs: pip install kokoro-onnx soundfile; KOKORO_DIR with kokoro-v1.0.int8.onnx + voices-v1.0.bin.
"""
import os, re, csv, json, subprocess, tempfile
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
SR = 48000
TOTAL = 360.0
N = int(TOTAL * SR)
rng = np.random.default_rng(7)

def t2s(s):
    m, s = s.split(":"); return int(m) * 60 + int(s)

shots = list(csv.DictReader(open(os.path.join(HERE, "..", "shots.csv"))))
for s in shots:
    s["start"], s["end"] = int(s["start"]), int(s["end"])
S = {s["shot"]: s for s in shots}

# --------------------------------------------------------------------------- voices
VOICES = {  # kokoro voice, speed, pitch shift in semitones
    "Milo": ("af_sky", 0.8, 3.0),
    "Pip": ("af_heart", 0.78, 1.0),
    "Narrator": ("bf_emma", 0.76, 0.0),
}

def pitch_shift(a, sr, semis):
    if not semis:
        return a
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav")
        sf.write(i, a, sr)
        r = 2 ** (semis / 12)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-af",
                        f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.5f}", o], check=True)
        b, _ = sf.read(o)
    return b

_k = None
def tts(who, text):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        kd = os.environ["KOKORO_DIR"]
        _k = Kokoro(os.path.join(kd, "kokoro-v1.0.int8.onnx"), os.path.join(kd, "voices-v1.0.bin"))
    v, sp, ps = VOICES[who]
    a, sr = _k.create(text, voice=v, speed=sp, lang="en-us")
    a = pitch_shift(a, sr, ps)
    # resample to SR
    idx = np.arange(0, len(a), sr / SR)
    a = np.interp(idx, np.arange(len(a)), a)
    a = a / (np.abs(a).max() + 1e-9) * 0.8
    return a.astype(np.float32)

def place(buf, clip, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(clip))
    buf[i:j] += clip[: j - i] * gain

dialogue = np.zeros(N, np.float32)
lines = []  # {who, text, start, end, shot}
srt = []
cache = os.path.join(OUT, "tts_cache"); os.makedirs(cache, exist_ok=True)

def voice_clip(who, text):
    key = re.sub(r"[^a-z0-9]+", "_", (who + "_" + text).lower())[:80]
    p = os.path.join(cache, key + ".wav")
    if os.path.exists(p):
        return sf.read(p, dtype="float32")[0]
    a = tts(who, text); sf.write(p, a, SR); return a

for s in shots:
    pairs = re.findall(r'(Milo|Pip|Narrator): "([^"]+)"', s["line"])
    t = s["start"] + 0.35
    for who, text in pairs:
        a = voice_clip(who, text)
        place(dialogue, a, t)
        d = len(a) / SR
        lines.append(dict(who=who, text=text, start=round(t, 3), end=round(t + d, 3), shot=s["shot"]))
        srt.append((t, t + d, text))
        if t + d > s["end"] + 0.05:
            print(f"WARNING {s['shot']} line runs past shot end: {t + d:.2f} > {s['end']}")
        t += d + 0.35

# extra vocal SFX (giggles, sneeze, effort, cheers) from the same voices
VOCAL = [("S17", 4.0, "Milo", "Ahh... choo!"), ("S30", 1.2, "Milo", "Hup!"), ("S30", 4.5, "Pip", "Hee hee!"),
         ("S31", 3.2, "Pip", "Hee hee hee!"), ("S31", 3.6, "Milo", "Ha ha!"), ("S16", 3.0, "Milo", "Yay!"),
         ("S10", 1.0, "Pip", "Oh!"), ("S14", 0.0, "Pip", "Ooh!"), ("S40", 0.2, "Milo", "Phooo!"),
         ("S43", 5.2, "Milo", "Yay!"), ("S38", 2.6, "Milo", "Phoo!"), ("S24", 4.5, "Milo", "Whoa!")]
for shot, off, who, text in VOCAL:
    a = voice_clip(who, text)
    t = S[shot]["start"] + off
    # keep vocal SFX clear of spoken lines in the same shot
    for L in lines:
        if L["shot"] == shot and L["start"] - 0.1 < t + len(a) / SR and t < L["end"] + 0.1:
            t = L["end"] + 0.25
    place(dialogue, a, t, 0.75)
    lines.append(dict(who=who, text=text, start=round(t, 3), end=round(t + len(a) / SR, 3), shot=shot, vocal=True))

json.dump(lines, open(os.path.join(OUT, "lines.json"), "w"), indent=1)

def fmt(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
with open(os.path.join(HERE, "..", "ep1_captions.srt"), "w") as f:
    for i, (a, b, txt) in enumerate(srt, 1):
        f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n{txt}\n\n")

# --------------------------------------------------------------------------- synth helpers
def T(d):
    return np.arange(int(d * SR)) / SR

def env_ad(d, a=0.005, k=6.0):
    t = T(d); e = np.exp(-k * t / d)
    att = np.minimum(1, t / max(a, 1e-4)); return e * att

def smooth(x, n):
    n = max(1, int(n)); k = np.ones(n) / n
    return np.convolve(x, k, mode="same")

def noise(d):
    return rng.standard_normal(int(d * SR))

def bell(f, d=1.2, k=5.0):
    t = T(d)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-3 * t) + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-6 * t)
    return s * env_ad(d, 0.002, k)

def sweep(f0, f1, d, wave=np.sin, vib=0.0):
    t = T(d); f = f0 * (f1 / f0) ** (t / d)
    if vib:
        f = f * (1 + 0.04 * np.sin(2 * np.pi * vib * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return wave(ph)

def nt(m):  # midi to Hz
    return 440 * 2 ** ((m - 69) / 12)

PENTA = [0, 2, 4, 7, 9]

def sfx_ting(): return 0.5 * bell(nt(88), 1.0, 6)
def sfx_sparkle():
    out = np.zeros(int(1.4 * SR))
    for i, m in enumerate([84, 88, 91, 93, 96, 100]):
        c = bell(nt(m), 0.8, 7) * 0.35; j = int(i * 0.07 * SR); out[j:j + len(c)] += c[: len(out) - j]
    return out
def sfx_twinkle():
    out = np.zeros(int(1.2 * SR))
    for i, m in enumerate([96, 91, 100]):
        c = bell(nt(m), 0.7, 8) * 0.3; j = int(i * 0.12 * SR); out[j:j + len(c)] += c[: len(out) - j]
    return out
def sfx_chime():
    out = np.zeros(int(1.8 * SR))
    for i, m in enumerate([72, 76, 79, 84]):
        c = bell(nt(m), 1.2, 5) * 0.4; j = int(i * 0.09 * SR); out[j:j + len(c)] += c[: len(out) - j]
    return out
def sfx_bigchime():
    a = sfx_chime(); b = np.pad(sfx_sparkle(), (int(0.3 * SR), 0))
    b = np.pad(b, (0, max(0, len(a) - len(b))))[: len(a)]
    return a + b * 0.8
def sfx_boing(): return 0.45 * sweep(160, 420, 0.45, vib=14) * env_ad(0.45, 0.005, 3)
def sfx_wobble(): return 0.35 * sweep(300, 220, 0.9, vib=9) * env_ad(0.9, 0.01, 3)
def sfx_hop(): return 0.5 * sweep(220, 90, 0.14) * env_ad(0.14, 0.002, 5)
def sfx_bwoop(): return 0.45 * sweep(520, 160, 1.0, vib=5) * env_ad(1.0, 0.02, 2.5)
def sfx_splash():
    n = noise(0.6); e = env_ad(0.6, 0.004, 7)
    return 0.4 * (n - smooth(n, 6)) * e + 0.2 * smooth(n, 20) * e
def sfx_bigsplash(): return np.concatenate([sfx_splash(), sfx_splash()[: int(0.3 * SR)] * 0.6]) * 1.2
def sfx_whoosh(d=1.2):
    n = noise(d); t = T(d); e = np.sin(np.pi * t / d) ** 2
    return 0.5 * smooth(n, 8) * e
def sfx_whir(d=3.0):
    t = T(d); n = smooth(noise(d), 4)
    return 0.25 * n * (0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)) * np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.5)
def sfx_click(): return 0.5 * bell(nt(96), 0.06, 9) + 0.2 * noise(0.06) * env_ad(0.06, 0.001, 12)
def sfx_flutter():
    out = np.zeros(int(1.0 * SR))
    for i in range(5):
        c = 0.15 * smooth(noise(0.08), 3) * env_ad(0.08, 0.005, 4); j = int(i * 0.15 * SR); out[j:j + len(c)] += c
    return out
def sfx_flaps():
    out = np.zeros(int(1.4 * SR))
    for i in range(7):
        c = 0.3 * smooth(noise(0.07), 10) * env_ad(0.07, 0.003, 5); j = int(i * 0.18 * SR); out[j:j + len(c)] += c
    return out
def sfx_rustle(d=0.8):
    n = noise(d) * (rng.random(int(d * SR)) < 0.03)
    return 0.6 * smooth(n, 3) * np.sin(np.pi * T(d) / d)
def sfx_birds(d=4.0):
    out = np.zeros(int(d * SR))
    for k in range(6):
        c = 0.12 * sweep(rng.uniform(2800, 3600), rng.uniform(3800, 4600), 0.12) * env_ad(0.12, 0.01, 3)
        j = int(rng.uniform(0, d - 0.3) * SR); out[j:j + len(c)] += c
    return out
def sfx_breeze(d=6.0):
    n = smooth(smooth(noise(d), 40), 40); t = T(d)
    return 1.6 * n * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t)) * np.minimum(1, t / 1) * np.minimum(1, (d - t) / 1)
def sfx_water(d=6.0):
    n = smooth(noise(d), 60); t = T(d)
    return 2.0 * n * (0.55 + 0.45 * np.sin(2 * np.pi * 0.6 * t)) * np.minimum(1, t / 1) * np.minimum(1, (d - t) / 1)
def sfx_flump(): return 0.6 * smooth(noise(0.3), 30) * env_ad(0.3, 0.003, 6) * 3
def sfx_hum(d=6.0):
    t = T(d)
    return 0.08 * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * (0.7 + 0.3 * np.sin(2 * np.pi * 3 * t)) * np.minimum(1, t) * np.minimum(1, d - t)
def sfx_shimmer(d=4.0):
    out = np.zeros(int(d * SR))
    for i in range(int(d * 10)):
        c = bell(nt(rng.choice([84, 86, 88, 91, 93, 96, 98, 100])), 0.6, 8) * 0.14
        j = int(i * 0.1 * SR); out[j:j + len(c)] += c[: max(0, len(out) - j)]
    return out * np.minimum(1, T(d) / 0.5)
def sfx_swell(d=3.0):
    t = T(d); out = np.zeros(len(t))
    for m in [60, 64, 67, 72, 76]:
        out += np.sin(2 * np.pi * nt(m) * t)
    return 0.06 * out * (t / d) ** 2 * np.minimum(1, (d - t) / 0.3 + 0.0001)

SFX = dict(ting=sfx_ting, sparkle=sfx_sparkle, twinkle=sfx_twinkle, chime=sfx_chime, bigchime=sfx_bigchime,
           boing=sfx_boing, wobble=sfx_wobble, hop=sfx_hop, bwoop=sfx_bwoop, splash=sfx_splash, bigsplash=sfx_bigsplash,
           whoosh=sfx_whoosh, whir=sfx_whir, click=sfx_click, flutter=sfx_flutter, flaps=sfx_flaps, rustle=sfx_rustle,
           birds=sfx_birds, breeze=sfx_breeze, water=sfx_water, flump=sfx_flump, hum=sfx_hum, shimmer=sfx_shimmer, swell=sfx_swell)

def hops(n, start, gap):
    return [("hop", start + i * gap) for i in range(n)]

# (shot, [(sfx, offset seconds)])  -- follows the Sound column of the timeline
CUES = {
    "S01": [("birds", 0.0), ("splash", 1.0), ("hop", 0.8)],
    "S02": [("boing", 0.2), ("wobble", 2.6)],
    "S03": [("twinkle", 0.6), ("bwoop", 1.6)],
    "S04": [("sparkle", 0.5)],
    "S06": [("flutter", 1.0)],
    "S09": [("flaps", 2.4)],
    "S10": [("twinkle", 1.5)],
    "S11": hops(2, 0.3, 0.45) + [("rustle", 4.6)],
    "S12": [("sparkle", 0.4)],
    "S13": hops(14, 0.2, 0.55),
    "S14": [("chime", 0.1)],
    "S16": [("chime", 0.2)],
    "S17": [("rustle", 1.0), ("rustle", 4.8)],
    "S18": [("twinkle", 0.2), ("rustle", 3.5)],
    "S19": [("sparkle", 0.4)],
    "S20": hops(12, 0.2, 0.55),
    "S21": [("water", 0.0)],
    "S22": [("water", 0.0)],
    "S23": [("chime", 0.2)],
    "S24": [("boing", 1.0), ("wobble", 1.6), ("flaps", 2.5), ("splash", 3.0)],
    "S25": [("twinkle", 0.3)],
    "S26": [("sparkle", 0.4)],
    "S27": [("hop", 0.5), ("splash", 0.6), ("hop", 2.5), ("hop", 3.0)],
    "S28": hops(16, 0.2, 0.48),
    "S29": [("breeze", 0.0), ("rustle", 2.0)],
    "S30": [("rustle", 3.0), ("breeze", 0.5)],
    "S31": [("rustle", 0.8), ("flump", 1.6), ("flump", 1.8)],
    "S32": [("sparkle", 0.4)],
    "S33": [("twinkle", 2.6)],
    "S34": hops(12, 0.1, 0.42),
    "S35": [("hum", 0.0), ("twinkle", 1.0)],
    "S37": [("bigchime", 0.2)],
    "S38": [("click", 3.4)],
    "S40": [("whoosh", 0.6), ("whir", 1.0), ("swell", 2.4), ("shimmer", 3.0)],
    "S41": [("shimmer", 0.0), ("whoosh", 0.3), ("whoosh", 4.0)],
    "S42": [("shimmer", 0.0), ("click", 3.0), ("bigchime", 3.1)],
    "S43": [("chime", 0.1)],
    "S46": [("ting", 0.3)], "S47": [("ting", 0.3)], "S48": [("ting", 0.3)], "S49": [("ting", 0.3), ("whir", 0.5)],
}
sfx = np.zeros(N, np.float32)
for shot, cues in CUES.items():
    for name, off in cues:
        place(sfx, SFX[name]().astype(np.float32), S[shot]["start"] + off, 1.0)
# S08: a ting on each of Pip's five color words, spread across her line
L8 = next(l for l in lines if l["shot"] == "S08" and not l.get("vocal"))
for i in range(5):
    place(sfx, sfx_ting().astype(np.float32), L8["start"] + (L8["end"] - L8["start"]) * (i + 0.15) / 5)

# --------------------------------------------------------------------------- music
THEME = [(0, 1), (2, 1), (4, 1), (7, 1), (9, 2), (7, 2), (4, 1), (7, 1), (9, 1), (12, 1), (9, 2), (7, 2),
         (4, 1), (2, 1), (0, 1), (2, 1), (4, 2), (7, 2), (4, 1), (2, 1), (2, 1), (4, 1), (0, 4)]
CHORDS = [[0, 4, 7], [7, 11, 14], [9, 12, 16], [5, 9, 12]]  # I V vi IV in C

def pluck(f, d, bright=1.0):
    t = T(d)
    s = np.sin(2 * np.pi * f * t) + 0.3 * bright * np.sin(4 * np.pi * f * t) + 0.12 * bright * np.sin(6 * np.pi * f * t)
    return s * env_ad(d, 0.004, 5)

def pad(fs, d):
    t = T(d); s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t) for f in fs)
    a = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return s * a / len(fs)

def music_section(d, mood, seed=0):
    r = np.random.default_rng(seed)
    P = dict(  # bpm, pad, bass, melody kind, bells, ticktock, vol
        intro=(84, 0.5, 0.0, "theme_soft", 0, 0, 0.55),
        sting=(100, 0.6, 0.6, "theme", 1, 0, 1.0),
        theme=(96, 0.45, 0.5, "theme", 0, 0, 0.6),
        adventure=(108, 0.5, 0.6, "walk", 0, 0, 0.7),
        curious=(92, 0.2, 0.0, "pizz", 0, 0, 0.55),
        bed=(92, 0.45, 0.35, "sparse", 0, 0, 0.45),
        travel=(120, 0.35, 0.7, "bounce", 0, 0, 0.75),
        travelfast=(132, 0.35, 0.7, "bounce", 0, 0, 0.8),
        ticktock=(90, 0.3, 0.0, None, 0, 1, 0.55),
        playful=(112, 0.2, 0.5, "pizz", 0, 0, 0.65),
        build=(104, 0.6, 0.6, "walk", 1, 0, 0.75),
        magical=(80, 0.6, 0.0, "bells", 1, 0, 0.65),
        full=(100, 0.6, 0.7, "theme", 1, 0, 0.9),
        warm=(80, 0.6, 0.3, "theme_soft", 0, 0, 0.5),
        outro=(96, 0.5, 0.5, "theme", 1, 0, 0.75),
    )[mood]
    bpm, padv, bassv, mel, bells, tick, vol = P
    beat = 60 / bpm
    out = np.zeros(int(d * SR))
    def add(clip, t, g):
        j = int(t * SR)
        if j >= len(out): return
        k = min(len(out), j + len(clip)); out[j:k] += clip[: k - j] * g
    bar = 4 * beat
    nbars = int(np.ceil(d / bar)) + 1
    for b in range(nbars):
        ch = CHORDS[b % 4]; t0 = b * bar
        if padv:
            add(pad([nt(60 + c) for c in ch], bar + 0.6), t0, 0.12 * padv)
        if bassv:
            for i in range(4 if mood.startswith("travel") else 2):
                step = bar / (4 if mood.startswith("travel") else 2)
                add(pluck(nt(36 + ch[0] + (7 if i % 2 else 0)), step * 0.95, 0.4), t0 + i * step, 0.22 * bassv)
        if tick:
            for i in range(4):
                add(bell(nt(84 if i % 2 == 0 else 79), 0.12, 10) * 0.25, t0 + i * beat, 1)
    if mel in ("theme", "theme_soft"):
        t = 0; i = 0
        while t < d:
            deg, ln = THEME[i % len(THEME)]
            add(pluck(nt(72 + deg), ln * beat * 0.95, 0.6 if mel == "theme_soft" else 1.0), t, 0.11 if mel == "theme_soft" else 0.14)
            if bells: add(bell(nt(84 + deg), 0.6, 6), t, 0.03)
            t += ln * beat; i += 1
    elif mel in ("walk", "bounce", "pizz", "sparse", "bells"):
        step = {"walk": 0.5, "bounce": 0.5, "pizz": 0.5, "sparse": 1.0, "bells": 0.5}[mel] * beat
        deg = 2; t = 0
        while t < d:
            if mel == "sparse" and r.random() < 0.45: t += step; continue
            if mel == "pizz" and r.random() < 0.3: t += step; continue
            deg = int(np.clip(deg + r.choice([-2, -1, 1, 2]), 0, 9))
            m = 72 + 12 * (deg // 5) + PENTA[deg % 5]
            if mel == "bells":
                add(bell(nt(m + 12), 1.0, 5), t, 0.08)
            elif mel == "pizz":
                add(pluck(nt(m), 0.18, 0.3) * env_ad(0.18, 0.002, 9), t, 0.16)
            else:
                add(pluck(nt(m), step * 0.9, 0.8), t, 0.12 if mel == "sparse" else 0.13)
            t += step
    return out * vol

MUSIC = [  # (start, end, mood) in seconds, from the Sound column
    (0, 11, "intro"), (15, 21, "sting"), (21, 50, "theme"), (50, 57, "adventure"), (57, 63, "curious"),
    (63, 76, "bed"), (76, 84, "travel"), (84, 91, "bed"), (91, 99, "ticktock"), (99, 105, "bed"),
    (105, 112, "playful"), (112, 125, "bed"), (125, 132, "travel"), (132, 139, "bed"), (139, 147, "ticktock"),
    (147, 153, "bed"), (153, 161, "playful"), (161, 174, "bed"), (174, 180, "travel"), (180, 188, "travelfast"),
    (188, 195, "bed"), (195, 202, "playful"), (202, 214, "bed"), (214, 228, "build"), (228, 235, "magical"),
    (235, 243, "ticktock"), (243, 264, "build"), (264, 278, "magical"), (278, 292, "full"), (292, 299, "warm"),
    (299, 330, "warm"), (330, 360, "outro"),
]
music = np.zeros(N, np.float32)
for k, (a, b, mood) in enumerate(MUSIC):
    seg = music_section(b - a + 0.6, mood, seed=k)
    fade = np.ones(len(seg)); f = int(0.4 * SR)
    fade[:f] = np.linspace(0, 1, f); fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR))
    if mood == "outro":
        tt = np.arange(len(seg)) / SR; fade *= np.clip((b - a - tt) / 3.0, 0, 1)  # fade over last 3 s
    place(music, (seg * fade).astype(np.float32), a)

# duck music under dialogue
voice_on = smooth((np.abs(dialogue) > 0.02).astype(np.float32), int(0.25 * SR))
voice_on = np.clip(smooth(np.clip(voice_on * 8, 0, 1), int(0.3 * SR)), 0, 1)
music *= (1 - 0.55 * voice_on)

def norm(x, peak):
    return x / (np.abs(x).max() + 1e-9) * peak

dialogue = dialogue.astype(np.float32)
music_n = norm(music, 0.30); sfx_n = norm(sfx, 0.45)
mix = dialogue * 0.9 + music_n + sfx_n
mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # soft limit
stereo = lambda x: np.stack([x, x], 1)
sf.write(os.path.join(OUT, "dialogue.wav"), stereo(dialogue), SR)
sf.write(os.path.join(OUT, "music.wav"), stereo(music_n), SR)
sf.write(os.path.join(OUT, "sfx.wav"), stereo(sfx_n), SR)
sf.write(os.path.join(OUT, "mix_raw.wav"), stereo(mix), SR)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(OUT, "mix_raw.wav"),
                "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", str(SR), os.path.join(OUT, "mix.wav")], check=True)
print("lines:", len([l for l in lines if not l.get("vocal")]), "audio done")
