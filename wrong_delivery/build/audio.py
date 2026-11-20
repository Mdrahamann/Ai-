"""The Wrong Delivery pilot: voices (Kokoro TTS), ambience, sound effects, original music, mix and subtitles.

Everything is generated from ../pilot.json, so the audio always matches the shot durations the timeline uses.

  python3 audio.py --measure    # speak every line once and print how well each line fits its shot
  python3 audio.py              # build out/voices/*.wav, out/{dialogue,ambience,sfx,music}.wav, out/mix.wav, out/pilot.srt

Needs: pip install kokoro-onnx soundfile numpy scipy; ffmpeg; KOKORO_DIR with kokoro-v1.0.int8.onnx + voices-v1.0.bin
(github.com/thewh1teagle/kokoro-onnx releases, tag model-files-v1.0).
The sound effects and music here are synthesized (no samples, no licence issues). They are pilot-grade: replace them with
licensed library sounds before a final release if you want a more realistic mix.
"""
import os, sys, json, re, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.environ.get("AUDIO_OUT") or os.path.join(HERE, "out"); VOX = os.path.join(OUT, "voices"); os.makedirs(VOX, exist_ok=True)
CACHE = os.path.join(HERE, "out", "tts_cache")  # voice cache shared by every config
SR = 48000
CFG = json.load(open(os.path.join(ROOT, os.environ.get("PILOT", "pilot.json"))))
SHOTS = CFG["shots"]
t0 = 0.0
for s in SHOTS:
    s["start"] = round(t0, 3); t0 += s["dur"]; s["end"] = round(t0, 3)
TOTAL = round(t0, 3)
N = int((TOTAL + 0.5) * SR)

# ------------------------------------------------------------------ voices
# Original generic voices from the open Kokoro model. They do not imitate any actor or game character.
VOICES = {"alex": ("am_michael", 0.92, -1.5), "mia": ("af_nicole", 1.0, -0.5)}
_k = None

def pitch_shift(a, sr, semis):
    if not semis: return a
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav"); sf.write(i, a, sr); r = 2 ** (semis / 12)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-af", f"asetrate={int(sr * r)},aresample={sr},atempo={1 / r:.5f}", o], check=True)
        return sf.read(o, dtype="float32")[0]

def speak(who, text):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        kd = os.environ["KOKORO_DIR"]; _k = Kokoro(os.path.join(kd, "kokoro-v1.0.int8.onnx"), os.path.join(kd, "voices-v1.0.bin"))
    v, sp, ps = VOICES[who]
    a, sr = _k.create(text, voice=v, speed=sp, lang="en-us")
    a = pitch_shift(np.asarray(a, np.float32), sr, ps)
    if sr != SR: a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype(np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz): a = a[max(0, nz[0] - 300): nz[-1] + 1500]
    return (a / (np.abs(a).max() + 1e-9) * 0.9).astype(np.float32)

def treat(a, style):
    """voice-over: close and dry with a little tail; room: natural reverb for on-screen lines."""
    chain = {"vo": "highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,aecho=0.7:0.5:70:0.12",
             "room": "highpass=f=100,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,aecho=0.8:0.6:28|52:0.2|0.12"}[style]
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav"); sf.write(i, np.concatenate([a, np.zeros(int(0.5 * SR), np.float32)]), SR)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", i, "-af", chain, "-ar", str(SR), o], check=True)
        b = sf.read(o, dtype="float32")[0]
    return (b / (np.abs(b).max() + 1e-9) * 0.9).astype(np.float32)

def voices():
    lines = []
    for s in SHOTS:
        for k, L in enumerate(s["lines"]):
            cache = CACHE; os.makedirs(cache, exist_ok=True)
            key = re.sub(r"[^a-z0-9]+", "_", f"{L['who']}_{L['text']}".lower())[:80]
            p = os.path.join(cache, key + ".npy")
            if os.path.exists(p): a = np.load(p)
            else: a = speak(L["who"], L["text"]); np.save(p, a)
            a = treat(a, L["style"])
            nz = np.where(np.abs(a) > 0.01)[0]; a = a[: nz[-1] + int(0.2 * SR)] if len(nz) else a
            start = s["start"] + L["at"]; end = start + len(a) / SR
            lines.append(dict(shot=s["id"], who=L["who"], text=L["text"], style=L["style"], start=round(start, 3), end=round(end, 3), dur=round(len(a) / SR, 3), a=a,
                              shot_end=s["end"], overhang=s.get("overhang", 0.0)))
    return lines

def export_wavs(lines):
    for L in lines:
        pad = np.zeros(int(0.3 * SR), np.float32)  # 0.3 s clean head and tail room
        sf.write(os.path.join(VOX, f"shot{L['shot']}_{L['who']}.wav"), np.concatenate([pad, L["a"], pad]), SR, subtype="PCM_16")

def measure(lines):
    print(f"total {TOTAL:.1f} s over {len(SHOTS)} shots")
    bad = False
    for L in lines:
        slack = L["shot_end"] + L["overhang"] - L["end"]
        flag = "OK " if slack >= 0.25 else "TOO LONG"
        bad |= slack < 0.25
        print(f"shot {L['shot']} {L['who']:5s} {L['dur']:.2f}s  starts {L['start']:.2f}  ends {L['end']:.2f}  shot ends {L['shot_end']:.2f}  slack {slack:+.2f}  {flag}")
    return bad

# ------------------------------------------------------------------ synthesis helpers
rng = np.random.default_rng(2026)
def T(d): return np.arange(int(d * SR)) / SR
def noise(d): return rng.standard_normal(int(d * SR)).astype(np.float32)
def _f(kind, x, f, order=4): return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x).astype(np.float32)
def lp(x, f): return _f("lowpass", x, f)
def hp(x, f): return _f("highpass", x, f)
def bp(x, lo, hi): return _f("bandpass", x, [lo, hi], 2)
def env(d, a=0.01, r=0.2):
    t = T(d); return np.minimum(1, t / max(a, 1e-4)) * np.minimum(1, (d - t) / max(r, 1e-4))
def slow(d, rate=0.3, depth=0.3, seed=0):
    r = np.random.default_rng(seed); k = max(2, int(d * rate) + 2)
    pts = 1 + depth * (r.random(k) * 2 - 1); return np.interp(T(d), np.linspace(0, d, k), pts).astype(np.float32)

def rain(d, level=1.0):
    n = noise(d)
    x = bp(n, 1800, 9500) * 0.55 + bp(noise(d), 400, 2200) * 0.35
    drops = (rng.random(len(x)) < 0.0007).astype(np.float32) * noise(d) * 4
    return (x + bp(drops, 2500, 7000)) * slow(d, 0.5, 0.15, 1) * level * 0.5

def rain_roof(d, level=1.0): return lp(rain(d, level), 1400) * 1.4 + lp(noise(d), 250) * 0.08 * level

def engine(d, f0, f1, level=1.0):
    t = T(d); f = (f0 + (f1 - f0) * (t / d) ** 1.3) * (1 + 0.01 * np.sin(2 * np.pi * 3 * t))
    ph = np.cumsum(f / SR); pulses = np.diff(np.floor(ph), prepend=0).astype(np.float32)
    x = lp(pulses, 900) * 18
    x = x + _f("bandpass", pulses, [110, 340], 2) * 25 + lp(noise(d), 500) * 0.15
    x = x * (1 + 0.15 * np.sin(2 * np.pi * f * 0.5 * t))
    return np.clip(x, -2, 2) * 0.35 * level

def tire_spray(d, level=1.0):
    return hp(noise(d), 1500) * 0.2 * level * slow(d, 1.2, 0.5, 2) * env(d, 0.3, 0.3) + lp(noise(d), 300) * 0.1 * level

def siren(d, dist=1.0, seed=0, level=1.0):
    t = T(d); f = 900 + 400 * np.sin(2 * np.pi * 0.28 * t + seed); ph = 2 * np.pi * np.cumsum(f) / SR
    s = lp(np.sign(np.sin(ph)).astype(np.float32) * 0.5 + np.sin(ph).astype(np.float32), 2600)
    e = np.zeros(len(s), np.float32); k = int(0.13 * SR); e[k:] += s[:-k] * 0.35; s = s + e
    return lp(s, 1800 if dist > 0.5 else 3500) * 0.12 * level * env(d, 0.6, 0.6)

def helicopter(d, level=1.0):
    t = T(d); chop = (0.55 + 0.45 * np.maximum(0, np.sin(2 * np.pi * 11 * t))) ** 2
    x = bp(noise(d), 120, 900) * chop * 1.2 + 0.25 * np.sin(2 * np.pi * 62 * t) * chop
    return x * level * 0.35 * np.minimum(1, (t / d) * 1.5 + 0.35) * env(d, 0.8, 0.5)

def club_door(d, bpm=124, level=1.0):
    t = T(d); out = np.zeros(len(t), np.float32); beat = 60 / bpm
    for i in range(int(d / beat) + 1):
        a = int(i * beat * SR); L = int(0.3 * SR)
        if a + L > len(out): break
        tt = np.arange(L) / SR; out[a:a + L] += np.sin(2 * np.pi * np.cumsum(45 + 80 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 9) * 1.2
        if i % 2: out[a:a + L] += (hp(noise(0.3), 5000)[:L] * np.exp(-tt * 40) * 0.05)
    bass = np.sin(2 * np.pi * 55 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * (bpm / 60 / 2) * t)) * 0.25
    return lp(out + bass, 260) * 0.8 * level

def crowd(d, level=1.0):
    x = np.zeros(int(d * SR), np.float32)
    for k in range(5):
        syl = np.abs(np.sin(2 * np.pi * (3 + k) * T(d) + k * 2)) ** 3
        x += bp(noise(d), 250 + 90 * k, 1300 + 200 * k) * syl * 0.18
    return x * slow(d, 0.4, 0.3, 4) * level

def wind(d, level=1.0):
    x = lp(noise(d), 500) * slow(d, 0.35, 0.6, 5) * 1.2 + bp(noise(d), 700, 1300) * 0.05 * slow(d, 0.2, 0.8, 6)
    return x * level * env(d, 1, 1)

def creak(d=1.4, level=1.0):
    t = T(d); f = 260 + 180 * np.sin(2 * np.pi * 0.9 * t) + 60 * np.sin(2 * np.pi * 7 * t)
    s = ((2 * ((np.cumsum(f) / SR) % 1) - 1) * 0.5).astype(np.float32)
    return bp(s + 0.3 * noise(d), 300, 1800) * level * 0.6 * env(d, 0.2, 0.4) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t) ** 2)

def steps(n, gap, wet=True, level=1.0, jitter=0.03):
    d = n * gap + 0.4; out = np.zeros(int(d * SR), np.float32); r = np.random.default_rng(11)
    for i in range(n):
        a = int((i * gap + r.uniform(-jitter, jitter) + 0.05) * SR); L = int(0.16 * SR); tt = np.arange(L) / SR
        s = lp(noise(0.16)[:L], 1500) * np.exp(-tt * 28) * 0.9 + np.sin(2 * np.pi * 85 * tt) * np.exp(-tt * 40) * 0.6
        if wet: s += hp(noise(0.16)[:L], 2500) * np.exp(-tt * 20) * 0.35
        if a + L < len(out): out[a:a + L] += s * (0.85 + 0.3 * r.random())
    return out * level

def latch(level=1.0):
    d = 0.5; out = np.zeros(int(d * SR), np.float32)
    for a_ in (0.0, 0.07):
        a = int(a_ * SR); L = int(0.05 * SR); tt = np.arange(L) / SR
        out[a:a + L] += (bp(noise(0.05)[:L], 1800, 6500) * np.exp(-tt * 120) + np.sin(2 * np.pi * 2800 * tt) * np.exp(-tt * 150) * 0.4)
    return out * level

def elec_pulse(d, level=1.0):
    t = T(d); trem = 0.5 + 0.5 * np.sin(2 * np.pi * 0.9 * t) ** 2
    x = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 55.6 * t) + 0.25 * np.sin(2 * np.pi * 110 * t)) * trem
    return (x * 0.35 + lp(noise(d), 800) * 0.03) * level * env(d, 0.6, 0.6)

def rustle(d=0.8, level=1.0):
    return hp(noise(d), 1800) * (rng.random(int(d * SR)) < 0.12) * np.sin(np.pi * T(d) / d) * 0.6 * level

def room_tone(d, level=1.0): return (lp(np.cumsum(noise(d)) / SR * 40, 180) * 0.08 + hp(noise(d), 4000) * 0.004) * level

def tension_sting(d, level=1.0):
    t = T(d); out = np.zeros(len(t), np.float32)
    for semi in (0, 7, 10, 13):  # dark cluster that climbs; original, not a quotation of any theme
        f = 55 * 2 ** ((semi + 3 * t / d) / 12); ph = np.cumsum(f) / SR
        out += ((2 * (ph % 1) - 1) * 0.3).astype(np.float32)
    versions = [lp(out, c) for c in (150, 400, 900, 2200, 5000)]
    pos = np.clip(t / d, 0, 1) * (len(versions) - 1); i0 = np.minimum(pos.astype(int), len(versions) - 2); w = pos - i0
    x = sum(np.where(i0 == k, (1 - w) * versions[k] + w * versions[k + 1], 0) for k in range(len(versions) - 1))
    riser = hp(noise(d), 1200) * (t / d) ** 2 * 0.15
    return (x + riser) * (t / d) ** 1.3 * level

def music_bed(d, level=1.0):
    t = T(d); bpm = 100; beat = 60 / bpm
    drone = lp((2 * ((np.cumsum(np.full(len(t), 55.0)) / SR) % 1) - 1).astype(np.float32), 300) * 0.5
    pad = sum(np.sin(2 * np.pi * f * t) * 0.12 for f in (110, 130.8, 164.8))
    pulse = np.zeros(len(t), np.float32)
    for i in range(int(d / (beat / 2)) + 1):
        a = int(i * beat / 2 * SR); L = int(0.22 * SR)
        if a + L > len(pulse): break
        tt = np.arange(L) / SR; note = 55 if i % 4 != 3 else 65.4
        pulse[a:a + L] += np.sin(2 * np.pi * note * tt) * np.exp(-tt * 8) * 0.5
    return (drone + pad * slow(d, 0.1, 0.4, 9) + pulse) * level * env(d, 1.0, 1.0)

# ------------------------------------------------------------------ sound design per shot (follows the script's sound column)
def place(buf, clip, t, g=1.0, fade=0.25):
    i = int(t * SR)
    if i >= len(buf) or i + len(clip) <= 0: return
    c = clip * g
    if fade and len(c) > 4 * int(fade * SR):
        f = int(fade * SR); c = c.copy(); c[:f] *= np.linspace(0, 1, f); c[-f:] *= np.linspace(1, 0, f)
    a = max(0, i); b = min(len(buf), i + len(c)); buf[a:b] += c[a - i: b - i]

def design(s):
    """returns (ambience layers, sfx cues) for a shot as lists of (generator, start offset, gain)."""
    d = s["dur"]; x = 0.35  # ambience beds start slightly before the cut and end after it (cross-fade)
    sid = s.get("sound", s["id"])  # a shot can borrow another shot's sound design
    if sid == "T0":
        return ([(lambda D: rain(D, 0.3), 0.0, 0.8), (lambda D: elec_pulse(D), 0.0, 0.8)], [])
    if sid == "T9":
        return ([(lambda D: room_tone(D, 1.0), 0.0, 1.0), (lambda D: rain(D, 0.08), 0.0, 0.5)], [])
    if sid == "01":
        return ([(lambda D: rain(D, 1.0), -x, 0.9), (lambda D: engine(D, 62, 118), -x, 1.0), (lambda D: tire_spray(D), -x, 0.9),
                 (lambda D: siren(D, 1.0, 0), 0.0, 1.0), (lambda D: siren(D, 1.0, 2), 0.7, 0.7)], [])
    if sid == "02":
        return ([(lambda D: club_door(D), -x, 0.9), (lambda D: crowd(D), -x, 0.7), (lambda D: rain(D, 0.45), -x, 0.9)], [(lambda: rustle(0.7), 2.7, 0.8)])
    if sid == "03":
        return ([(lambda D: wind(D, 1.0), -x, 1.0), (lambda D: rain(D, 0.25), -x, 0.7), (lambda D: room_tone(D), -x, 0.5)],
                [(lambda: creak(1.4), 0.3, 0.8), (lambda: creak(1.0), 3.2, 0.6), (lambda: steps(4, 0.62, True, 0.5), 2.0, 0.9)])
    if sid == "04":
        return ([(lambda D: rain_roof(D, 1.0), -x, 1.0), (lambda D: elec_pulse(D), 0.7, 0.9), (lambda D: lp(siren(D, 1.0, 1), 900), 0.0, 0.6)],
                [(lambda: latch(), 0.9, 1.0)])
    if sid == "05":
        return ([(lambda D: rain(D, 0.8), -x, 0.9), (lambda D: siren(D, 0.0, 3), -x, 1.0), (lambda D: helicopter(D), -x, 1.0), (lambda D: tire_spray(D, 0.25), -x, 0.4)],
                [(lambda: steps(int((d - 0.2) / 0.3), 0.3, True, 0.9, 0.02), 0.0, 1.0)])
    if sid == "06":
        return ([(lambda D: room_tone(D, 1.0), -x, 1.2), (lambda D: rain(D, 0.08), -x, 0.5)], [(lambda: tension_sting(min(4.0, d - 0.6)), d - min(4.0, d - 0.6), 1.0)])
    return ([], [])

def build():
    lines = voices(); export_wavs(lines)
    bad = measure(lines)
    dlg = np.zeros(N, np.float32)
    for L in lines: place(dlg, L["a"], L["start"], 1.0, 0)
    amb = np.zeros(N, np.float32); sfx = np.zeros(N, np.float32)
    for s in SHOTS:
        layers, cues = design(s)
        for gen, off, g in layers:
            D = s["dur"] + (0.35 if off < 0 else 0) + 0.35 - max(0, off)
            place(amb, gen(D), s["start"] + off, g, 0.3)
        for gen, off, g in cues: place(sfx, gen().astype(np.float32), s["start"] + off, g, 0.02)
    mus = music_bed(TOTAL + 0.4, 1.0)
    # music level per shot (quiet under dialogue scenes, rises into the final sting)
    gain = np.ones(N, np.float32)
    for s in SHOTS:
        lv = {"01": 0.5, "02": 0.25, "03": 0.4, "04": 0.2, "05": 0.55, "06": 0.45, "T0": 0.6, "T9": 0.5}.get(s["id"], 0.4)
        a, b = int(s["start"] * SR), int(s["end"] * SR); gain[a:b] = lv
    gain = np.convolve(gain, np.ones(int(0.5 * SR)) / int(0.5 * SR), mode="same")
    mus = np.pad(mus, (0, max(0, N - len(mus))))[:N] * gain
    von = np.clip(np.convolve((np.abs(dlg) > 0.02).astype(np.float32), np.ones(int(0.35 * SR)) / int(0.35 * SR), mode="same") * 6, 0, 1)
    duck = 1 - 0.6 * von
    norm = lambda x, p: x / (np.abs(x).max() + 1e-9) * p
    mix = dlg * 1.0 + norm(amb, 0.17) * duck + norm(sfx, 0.30) * (1 - 0.45 * von) + norm(mus, 0.12) * duck
    end = int(TOTAL * SR); mix = mix[:end]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))  # hard cut to black on the last frame
    for nm, x in (("dialogue", dlg[:end]), ("ambience", amb[:end]), ("sfx", sfx[:end]), ("music", mus[:end])):
        sf.write(os.path.join(OUT, nm + ".wav"), np.stack([x, x], 1), SR, subtype="PCM_16")
    sf.write(os.path.join(OUT, "mix_raw.wav"), np.stack([mix, mix], 1), SR)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(OUT, "mix_raw.wav"), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(SR), "-c:a", "pcm_s16le",
                    os.path.join(OUT, "mix.wav")], check=True)
    def fmt(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000); return f"{h:02d}:{m:02d}:{s_:02d},{ms:03d}"
    with open(os.path.join(OUT, "pilot.srt"), "w") as f:
        for i, L in enumerate(lines, 1): f.write(f"{i}\n{fmt(L['start'])} --> {fmt(L['end'])}\n{L['text']}\n\n")
    json.dump([{k: v for k, v in L.items() if k != "a"} for L in lines], open(os.path.join(OUT, "lines.json"), "w"), indent=1)
    print("audio built:", TOTAL, "s", "(a line is too long for its shot: edit pilot.json)" if bad else "(all lines fit)")
    return 1 if bad else 0

if __name__ == "__main__":
    if "--measure" in sys.argv:
        sys.exit(1 if measure(voices()) else 0)
    sys.exit(build())
