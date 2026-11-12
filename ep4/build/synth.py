"""Shared synth helpers for Milo & Pip soundtracks (sound effects, bells, theme music).
Extracted from ep1/build/audio.py so every episode sounds like the same show."""
import numpy as np
SR = 48000
rng = np.random.default_rng(7)

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

