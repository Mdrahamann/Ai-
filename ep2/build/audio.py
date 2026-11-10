"""Episode 2 soundtrack: voices (Kokoro TTS), music bed and sound effects, timed from ../plan.py.

Writes out/lines.json (who speaks when, for the renderer), out/mix.wav and ../ep2_captions.srt.
KOKORO_DIR must hold kokoro-v1.0.int8.onnx and voices-v1.0.bin.
"""
import os, re, sys, json, subprocess, tempfile
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import plan
from synth import *  # SR, T, env_ad, smooth, noise, bell, sweep, nt, SFX, music_section, pad, pluck ...

plan.check()
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
N = int(360 * SR)
S = {s["id"]: s for s in plan.SHOTS}

# ------------------------------------------------------------------ voices (same as episode 1)
VOICES = {"Milo": ("af_sky", 0.8, 3.0), "Pip": ("af_heart", 0.78, 1.0), "Narrator": ("bf_emma", 0.76, 0.0)}
_k = None

def pitch_shift(a, sr, semis):
    if not semis: return a
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav")
        sf.write(i, a, sr); r = 2 ** (semis / 12)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-af", f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.5f}", o], check=True)
        return sf.read(o)[0]

def voice_clip(who, text, speed_mul=1.0):
    cache = os.path.join(OUT, "tts_cache"); os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, re.sub(r"[^a-z0-9]+", "_", f"{who}_{speed_mul}_{text}".lower())[:90] + ".wav")
    if os.path.exists(p): return sf.read(p, dtype="float32")[0]
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        kd = os.environ["KOKORO_DIR"]
        _k = Kokoro(os.path.join(kd, "kokoro-v1.0.int8.onnx"), os.path.join(kd, "voices-v1.0.bin"))
    v, sp, ps = VOICES[who]
    a, sr = _k.create(text, voice=v, speed=sp * speed_mul, lang="en-us")
    a = pitch_shift(a, sr, ps)
    a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    a = (a / (np.abs(a).max() + 1e-9) * 0.8).astype(np.float32)
    sf.write(p, a, SR); return a

def place(buf, clip, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0: return
    j = min(len(buf), i + len(clip)); buf[i:j] += clip[: j - i] * gain

dialogue = np.zeros(N, np.float32); lines = []; srt = []
QUIET = {"S30": 0.55, "S24": 0.8, "S26": 0.8, "S38": 0.85}  # whisper / soft delivery
SLOW = {"S30": 0.85, "S24": 0.9, "S53": 0.92}
for s in plan.SHOTS:
    t = s["start"] + 0.35
    for who, text in s["lines"]:
        a = voice_clip(who, text, SLOW.get(s["id"], 1.0))
        place(dialogue, a, t, QUIET.get(s["id"], 1.0))
        d = len(a) / SR
        lines.append(dict(who=who, text=text, start=round(t, 3), end=round(t + d, 3), shot=s["id"]))
        srt.append((t, t + d, text))
        if t + d > s["end"] + 0.05: print(f"WARNING {s['id']} runs past its end: {t + d:.2f} > {s['end']}")
        t += d + 0.35

VOCAL = [("S09", 4.6, "Pip", "Hee hee!"), ("S10", 4.2, "Milo", "Ha ha ha!"), ("S10", 4.4, "Pip", "Hee hee hee!"),
         ("S15", 3.6, "Milo", "Hmph!"), ("S17", 1.5, "Milo", "Ugh!"), ("S17", 4.2, "Milo", "Grr!"),
         ("S19", 1.0, "Milo", "Oh..."), ("S39", 3.3, "Pip", "Hee hee."), ("S39", 3.6, "Milo", "Heh."),
         ("S44", 3.0, "Milo", "Ooh!"), ("S51", 4.5, "Milo", "Yay!"), ("S52", 3.2, "Pip", "Hee hee hee!"), ("S52", 3.5, "Milo", "Ha ha!")]
for shot, off, who, text in VOCAL:
    a = voice_clip(who, text); t = S[shot]["start"] + off
    for L in lines:
        if L["shot"] == shot and not L.get("vocal") and L["start"] - 0.1 < t + len(a) / SR and t < L["end"] + 0.1:
            t = L["end"] + 0.25
    place(dialogue, a, t, 0.7)
    lines.append(dict(who=who, text=text, start=round(t, 3), end=round(t + len(a) / SR, 3), shot=shot, vocal=True))
json.dump(lines, open(os.path.join(OUT, "lines.json"), "w"), indent=1)

def fmt(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s_:02d},{ms:03d}"
with open(os.path.join(HERE, "..", "ep2_captions.srt"), "w") as f:
    for i, (a, b, txt) in enumerate(srt, 1): f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n{txt}\n\n")

# ------------------------------------------------------------------ episode 2 sound effects
wr = np.random.default_rng(42)  # fixed seed: the wind motif is the exact same sound every time

def wind_motif():
    """Rising wind then the big gust (~4.5 s). Identical every call."""
    r = np.random.default_rng(42); d = 4.5; t = T(d)
    n = r.standard_normal(len(t))
    low = smooth(smooth(n, 60), 30) * 2.2
    hi = (n - smooth(n, 4)) * 0.18
    env = np.clip(t / 3.0, 0, 1) ** 2 * 0.6 + 0.9 * np.exp(-((t - 3.3) / 0.45) ** 2)
    howl = 0.05 * np.sin(2 * np.pi * np.cumsum(300 + 180 * np.clip(t / 3.3, 0, 1)) / SR) * env
    flutter = (r.random(len(t)) < 0.02) * r.standard_normal(len(t)) * 0.5 * np.clip((t - 2.5), 0, 1)
    return (low + hi) * env * 0.5 + howl + smooth(flutter, 3)

def rip(d=0.6, big=False):
    n = noise(d); t = T(d)
    crack = (rng.random(len(t)) < (0.25 if big else 0.18)) * n
    return 0.9 * smooth(crack, 2) * env_ad(d, 0.003, 2.5 if big else 4) + 0.15 * (n - smooth(n, 3)) * env_ad(d, 0.003, 6)

def tape_screech(d=0.9):
    t = T(d); n = noise(d)
    return 0.35 * (n - smooth(n, 2)) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t)) * np.sin(np.pi * t / d)

def thump():
    a = 0.7 * smooth(noise(0.25), 40) * env_ad(0.25, 0.002, 6) * 3
    a[: int(0.2 * SR)] += 0.4 * sweep(110, 60, 0.2) * env_ad(0.2, 0.002, 6)
    return a
def creak(): return 0.18 * sweep(380, 260, 0.8, wave=lambda p: np.sign(np.sin(p)) * 0.5 + np.sin(p) * 0.5, vib=11) * np.sin(np.pi * T(0.8) / 0.8)
def steps(n=6, gap=0.35):
    out = np.zeros(int((n * gap + 0.4) * SR))
    for i in range(n): place(out, thump() * 0.5, i * gap)
    return out
def rewind(): return 0.35 * sweep(2000, 300, 1.0, vib=30) * np.sin(np.pi * T(1.0)) + 0.25 * sfx_whoosh(1.0)
def chimes3():
    out = np.zeros(int(3.6 * SR))
    for i, m in enumerate([79, 76, 72]): place(out, bell(nt(m), 2.0, 3.5) * 0.35, i * 0.6)
    return out
def breath(inhale=True, d=2.4):
    n = smooth(noise(d), 10) - smooth(noise(d), 80); t = T(d)
    e = np.sin(np.pi * t / d) ** (1.2 if inhale else 0.8)
    return 0.45 * n * e
def thwip(): return 0.3 * sweep(900, 2400, 0.12) * env_ad(0.12, 0.002, 4)
def peel(): return 0.3 * tape_screech(0.4)
def fwump(): return 0.6 * smooth(noise(0.35), 50) * env_ad(0.35, 0.02, 4) * 3
def tummy(): return 0.2 * sweep(200, 500, 0.6, vib=6) * np.sin(np.pi * T(0.6) / 0.6) + 0.2 * sfx_whoosh(0.6)
def stringnote(m, d=2.5):
    t = T(d); f = nt(m)
    return 0.18 * (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)) * np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.6)
def piano(m, d=2.0): return 0.4 * pluck(nt(m), d, 0.7)
def breeze(d=6.0): return sfx_breeze(d) * 0.8

FX = dict(wind=wind_motif, rip=lambda: rip(0.6), bigrip=lambda: rip(1.3, True), tape=tape_screech, stamp=thump, creak=creak,
          steps=steps, rewind=rewind, chimes=chimes3, inhale=lambda: breath(True), exhale=lambda: breath(False, 3.0),
          thwip=thwip, peel=peel, fwump=fwump, tummy=tummy, breeze=breeze, breeze3=lambda: breeze(3.0),
          lownote=lambda: piano(45, 3.0), sniffpiano=lambda: piano(64, 2.5))
FX = {**SFX, **FX}
CUES = {
    "S01": [("wind", 0.6), ("rustle", 1.5)],               # gust peaks at ~0:05.3, rip right after
    "S02": [("rip", 1.0)],
    "S03": [("boing", 0.2)],
    "S04": [("lownote", 0.3), ("breeze3", 0.0)],
    "S05": [("rewind", 0.0), ("flutter", 0.6)],
    "S06": [("creak", 1.0), ("flutter", 3.5)],
    "S08": [("ting", 1.0), ("ting", 3.5), ("ting", 6.0), ("rustle", 0.3), ("rustle", 2.8), ("rustle", 5.3)],
    "S09": [("thwip", 0.6), ("flaps", 1.4)],
    "S10": [("peel", 1.0), ("sparkle", 2.4)],
    "S11": [("chime", 0.3)],
    "S12": [("creak", 0.0), ("steps", 0.8)],
    "S13": [("wind", -2.6), ("rip", 1.6)],                  # same motif, quieter (gain below)
    "S15": [("stamp", 1.2), ("rustle", 2.0)],
    "S16": [("rustle", 4.8)],
    "S17": [("tape", 0.5), ("thwip", 1.6), ("tape", 2.6), ("thwip", 3.4), ("flaps", 4.6)],
    "S18": [("tape", 0.4), ("bigrip", 1.4)],
    "S19": [("breeze3", 2.0)],
    "S20": [("breeze", 0.5), ("birds", 3.0)],
    "S21": [("stamp", 0.5), ("bwoop", 0.4), ("stamp", 3.4), ("stamp", 3.9)],
    "S22": [("stamp", 0.3), ("rustle", 1.0)],
    "S23": [("sniffpiano", 1.0)],
    "S24": [("chimes", 2.2)],
    "S25": [("tummy", 3.6)],
    "S26": [("breeze3", 2.0)],
    "S27": [("breeze", 0.0)],
    "S29": [("chimes", 2.5)],
    "S30": [("chimes", 0.3), ("inhale", 3.3), ("exhale", 5.0)],
    "S31": [("inhale", 0.4), ("exhale", 2.6), ("inhale", 4.6)],
    "S34": [("rustle", 0.6), ("rustle", 1.4)],
    "S37": [("flutter", 2.5)],
    "S42": [("fwump", 3.5), ("boing", 3.2)],
    "S44": [("rustle", 0.4), ("sparkle", 1.6)],
    "S45": [("rustle", 1.0), ("rustle", 3.0), ("rustle", 5.0)],
    "S46": [("rustle", 3.0), ("sparkle", 4.8)],
    "S47": [("sparkle", 1.0)],
    "S48": [("wind", 3.0)],                                 # same rising wind; gust lands in S49
    "S49": [("whir", 1.2)],
    "S50": [("whir", 0.0), ("whir", 2.9), ("whir", 5.8), ("shimmer", 0.5)],
    "S51": [("bigchime", 0.6), ("whir", 0.0), ("whir", 2.9)],
    "S52": [("wind", -2.8), ("flutter", 1.4)],
    "S53": [("whir", 0.0), ("whir", 2.9)],
    "S54": [("whir", 0.0), ("sparkle", 1.0)],
}
GAIN = {"S13": 0.5, "S52": 0.45}
sfx = np.zeros(N, np.float32)
for shot, cues in CUES.items():
    for name, off in cues:
        place(sfx, FX[name]().astype(np.float32) * GAIN.get(shot, 1.0), S[shot]["start"] + off)

# ------------------------------------------------------------------ music
def uneasy(d):
    out = np.zeros(int(d * SR)); bar = 3.2
    for b in range(int(d / bar) + 1):
        ch = [[57, 60, 64], [53, 57, 60], [52, 55, 59], [57, 60, 64]][b % 4]
        place(out, pad([nt(m) for m in ch], bar + 0.6) * 0.12, b * bar)
        place(out, stringnote(ch[0] - 12, bar) * 0.8, b * bar)
    return out
def sad_piano(d):
    out = np.zeros(int(d * SR))
    for i, m in enumerate([64, 62, 60, 59, 57, 60]):
        if i * 1.4 < d: place(out, piano(m, 2.4) * 0.5, i * 1.4)
    return out
def softpad(d):
    out = np.zeros(int(d * SR)); bar = 3.0
    for b in range(int(d / bar) + 1):
        place(out, pad([nt(m) for m in [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]][b % 4]], bar + 0.6) * 0.1, b * bar)
    return out

MUSIC = [  # (start, end, mood)
    (0.0, 6.4, "theme"), (15, 35, "warm"), (35, 43, "adventure"), (43, 57, "playful"), (57, 65, "full"), (65, 70, "bed"),
    (75, 94, "uneasy"), (94, 101, "playful"), (121, 135, "uneasy"), (135, 142, "sadpiano"), (142, 165, "softpad"),
    (172, 186, "softpad"), (186, 202, "softpad"), (202, 214, "ticktock"), (214, 255, "warm"), (255, 282, "theme"),
    (282, 291, "build"), (291, 307, "full"), (307, 360, "outro"),
]
music = np.zeros(N, np.float32)
for k, (a, b, mood) in enumerate(MUSIC):
    d = b - a + 0.6
    seg = {"uneasy": uneasy, "sadpiano": sad_piano, "softpad": softpad}.get(mood, lambda d: music_section(d, mood, seed=k + 11))(d)
    fade = np.ones(len(seg)); fi = int(0.5 * SR); fo = int(0.6 * SR)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    if mood == "outro":
        fade *= np.clip((b - a - np.arange(len(seg)) / SR) / 3.0, 0, 1)
    if a == 0.0:  # music cuts out sharply on the rip
        fade[-int(0.08 * SR):] = 0; fade[int(6.3 * SR) - int(0.05 * SR):] = 0
    place(music, (seg * fade).astype(np.float32), a)

voice_on = np.clip(smooth(np.clip(smooth((np.abs(dialogue) > 0.02).astype(np.float32), int(0.25 * SR)) * 8, 0, 1), int(0.3 * SR)), 0, 1)
music *= (1 - 0.55 * voice_on)

def norm(x, peak): return x / (np.abs(x).max() + 1e-9) * peak
mix = dialogue * 0.9 + norm(music, 0.30) + norm(sfx, 0.5)
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
sf.write(os.path.join(OUT, "mix_raw.wav"), np.stack([mix, mix], 1), SR)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(OUT, "mix_raw.wav"), "-af", "loudnorm=I=-15:TP=-1.5:LRA=11",
                "-ar", str(SR), os.path.join(OUT, "mix.wav")], check=True)
print("audio done:", len([l for l in lines if not l.get("vocal")]), "lines")
