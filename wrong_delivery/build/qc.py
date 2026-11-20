"""Quality checks for AI-generated clips and the final export of the pilot.

  python3 qc.py clip clips/shot01.mp4 --keyframe /path/SHOT_01_CAR_CHASE.png --need 5.0
  python3 qc.py final final/the_wrong_delivery_pilot.mp4

Each check returns PASS, REVIEW (a person must look) or FAIL. Writes a contact sheet (frames every 0.5 s plus the four
corners) next to the report so you and I can inspect it by eye.

IMPORTANT: these are heuristics. They catch the common failures (a still image with a camera zoom, frozen frames, watermarks
on a moving scene, low resolution, a clip that does not start from the keyframe, cuts and glitches). They can NOT confirm
that a face matches the character sheet, that hands are right, that wheels rotate plausibly or that signs are readable.
Those are listed in every report as "needs human review" and must be looked at on the contact sheet.
"""
import os, sys, json, subprocess, argparse
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))

def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f"ffprobe failed on {path}: {r.stderr.strip()}")
    j = json.loads(r.stdout); v = next((s for s in j["streams"] if s["codec_type"] == "video"), None); a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if not v: raise RuntimeError(f"{path} has no video stream")
    num, den = (v.get("avg_frame_rate") or "0/1").split("/"); fps = float(num) / float(den) if float(den) else 0.0
    return dict(width=int(v["width"]), height=int(v["height"]), fps=round(fps, 3), duration=float(j["format"].get("duration", v.get("duration", 0))),
                vcodec=v.get("codec_name"), acodec=a.get("codec_name") if a else None, bitrate=int(j["format"].get("bit_rate", 0)),
                size_mb=round(os.path.getsize(path) / 1e6, 2))

def sample(path, step=0.25, max_w=640):
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 24; n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); out = []
    t = 0.0
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
        ok, f = cap.read()
        if not ok or int(round(t * fps)) >= n: break
        h, w = f.shape[:2]; s = max_w / w
        out.append((round(t, 3), cv2.resize(f, (max_w, int(h * s)), interpolation=cv2.INTER_AREA))); t += step
    cap.release(); return out

def ssim(a, b):
    a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float64); b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float64)
    if a.shape != b.shape: b = cv2.resize(b, (a.shape[1], a.shape[0]))
    C1, C2 = 6.5025, 58.5225; k = (11, 11)
    mu_a, mu_b = cv2.GaussianBlur(a, k, 1.5), cv2.GaussianBlur(b, k, 1.5)
    saa = cv2.GaussianBlur(a * a, k, 1.5) - mu_a ** 2; sbb = cv2.GaussianBlur(b * b, k, 1.5) - mu_b ** 2; sab = cv2.GaussianBlur(a * b, k, 1.5) - mu_a * mu_b
    return float((((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (saa + sbb + C2))).mean())

# ------------------------------------------------------------------ individual checks
def check_resolution(p, expect):
    if p["width"] >= expect[0] and p["height"] >= expect[1]: return "PASS", f"{p['width']}x{p['height']} native"
    if p["width"] >= 1280 and p["height"] >= 720: return "REVIEW", f"native {p['width']}x{p['height']}: any 1080p export is upscaled, not true 1080p"
    return "FAIL", f"native {p['width']}x{p['height']} is below 720p"

def check_fps(p): return ("PASS", f"{p['fps']} fps") if abs(p["fps"] - 24) < 0.1 else ("REVIEW", f"{p['fps']} fps (the timeline conforms it to 24)")

def check_freeze(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "freezedetect=n=-55dB:d=0.4", "-an", "-f", "null", "-"], capture_output=True, text=True)
    durs = [float(l.split("freeze_duration:")[1].strip()) for l in r.stderr.splitlines() if "freeze_duration:" in l]
    total = sum(durs)
    return (("PASS", "no frozen frames") if total < 0.3 else ("REVIEW", f"{total:.1f} s of near-frozen video") if total < 1.5 else ("FAIL", f"{total:.1f} s of frozen video")), total

def check_watermark(frames, ignore=()):
    """Look for a static, high-contrast overlay in a corner while the rest of the picture changes."""
    g = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for _, f in frames]); n, h, w = g.shape
    if n < 6: return "REVIEW", "too few frames to test", {}
    std = g.std(0); mean = g.mean(0).astype(np.uint8); edges = cv2.Canny(mean, 60, 140) > 0
    ph, pw = int(h * 0.16), int(w * 0.24)
    boxes = {"top_left": (0, 0), "top_right": (0, w - pw), "bottom_left": (h - ph, 0), "bottom_right": (h - ph, w - pw)}
    def stat(y, x):
        e = edges[y:y + ph, x:x + pw]; s = std[y:y + ph, x:x + pw] < 3.0
        return float(e.mean()), float((e & s).sum() / max(e.sum(), 1))
    base = [stat(y, x)[1] for y in range(int(h * 0.2), h - ph - int(h * 0.2), ph) for x in range(int(w * 0.2), w - pw - int(w * 0.2), pw)]
    b = float(np.median(base)) if base else 1.0
    scene_moves = float((std > 3.0).mean()) > 0.08
    res = {}; flagged = []
    for k, (y, x) in boxes.items():
        ed, st = stat(y, x); res[k] = dict(edge_density=round(ed, 3), static_edge_share=round(st, 2))
        if k in ignore: res[k]["ignored"] = "our own on-screen label"; continue
        if scene_moves and ed > 0.02 and st > 0.9 and st - b > 0.25: flagged.append(k)
    if flagged: return "FAIL", f"static overlay detected in {', '.join(flagged)}: probably a watermark or logo (check the corner crops)", res
    if not scene_moves: return "REVIEW", "scene is almost static, so a watermark cannot be detected automatically: look at the corner crops", res
    return "PASS", "no static corner overlay found (still verify the corner crops by eye)", res

def check_motion(frames):
    """Separate camera motion (zoom/pan, fitted as a similarity transform) from independent motion of people, cars, water."""
    if len(frames) < 4: return "REVIEW", "too few frames", {}
    small = [cv2.cvtColor(cv2.resize(f, (480, int(480 * f.shape[0] / f.shape[1]))), cv2.COLOR_BGR2GRAY) for _, f in frames]
    h, w = small[0].shape; ys, xs = np.mgrid[8:h - 8:16, 8:w - 8:16]
    pts = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float32)
    frac, glob, scale = [], [], []
    for a, b in zip(small[:-1], small[1:]):
        fl = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 21, 3, 5, 1.1, 0)
        d = fl[pts[:, 1].astype(int), pts[:, 0].astype(int)]
        M, _ = cv2.estimateAffinePartial2D(pts, pts + d, method=cv2.RANSAC, ransacReprojThreshold=0.6)
        if M is None: continue
        gx, gy = np.meshgrid(np.arange(w), np.arange(h)); fx = M[0, 0] * gx + M[0, 1] * gy + M[0, 2] - gx; fy = M[1, 0] * gx + M[1, 1] * gy + M[1, 2] - gy
        res = np.hypot(fl[..., 0] - fx, fl[..., 1] - fy); frac.append(float((res > 1.2).mean())); glob.append(float(np.hypot(M[0, 2], M[1, 2])))
        scale.append(float(np.hypot(M[0, 0], M[1, 0]) - 1))
    if not frac: return "REVIEW", "motion could not be estimated", {}
    m = dict(independent_motion_share=round(float(np.mean(frac)), 4), camera_shift_px=round(float(np.mean(glob)), 2), camera_zoom_per_step=round(float(np.mean(scale)), 4))
    s = m["independent_motion_share"]
    if s < 0.015: return "FAIL", f"almost no independent motion ({s:.2%} of pixels): looks like a still image with a camera move", m
    if s < 0.04: return "REVIEW", f"little independent motion ({s:.2%} of pixels): check that people/cars really move", m
    return "PASS", f"independent motion on {s:.1%} of the picture (people, vehicles, water or rain; confirm by eye)", m

def check_keyframe(frames, keyframe):
    if not keyframe or not os.path.exists(keyframe): return "REVIEW", "no keyframe given or found", {}
    k = cv2.imread(keyframe); h, w = frames[0][1].shape[:2]; k = cv2.resize(k, (w, h), interpolation=cv2.INTER_AREA)
    first = ssim(frames[0][1], k); series = [ssim(frames[0][1], f) for _, f in frames]
    steps = [ssim(a[1], b[1]) for a, b in zip(frames[:-1], frames[1:])]
    m = dict(first_frame_vs_keyframe_ssim=round(first, 3), last_vs_first_ssim=round(series[-1], 3), lowest_consecutive_ssim=round(min(steps), 3) if steps else None)
    notes = []; st = "PASS"
    if first < 0.35: st = "FAIL"; notes.append(f"first frame does not match the keyframe (SSIM {first:.2f}): the tool may not have used it")
    elif first < 0.6: st = "REVIEW"; notes.append(f"first frame only loosely matches the keyframe (SSIM {first:.2f})")
    if steps and min(steps) < 0.10: st = "FAIL"; notes.append(f"abrupt change between frames (SSIM {min(steps):.2f}): a cut, morph or glitch")
    elif steps and min(steps) < 0.25 and st == "PASS": st = "REVIEW"; notes.append(f"large frame-to-frame change (SSIM {min(steps):.2f}): look for a jump or morph")
    return st, "; ".join(notes) or f"starts from the keyframe (SSIM {first:.2f}), no abrupt jumps", m

def contact_sheet(frames, path, every=0.5, cols=4):
    pick = [f for f in frames if abs((f[0] / every) - round(f[0] / every)) < 1e-6] or frames
    if len(pick) > 16: pick = pick[:: int(np.ceil(len(pick) / 16))]
    th = []
    for t, f in pick:
        im = cv2.resize(f, (480, int(480 * f.shape[0] / f.shape[1]))); cv2.putText(im, f"{t:.1f}s", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2); th.append(im)
    rows = (len(th) + cols - 1) // cols; hh, ww = th[0].shape[:2]; sheet = np.full((rows * hh + 150, cols * ww, 3), 255, np.uint8)
    for i, im in enumerate(th): sheet[(i // cols) * hh:(i // cols + 1) * hh, (i % cols) * ww:(i % cols + 1) * ww] = im
    f0 = frames[len(frames) // 2][1]; H, Wd = f0.shape[:2]; ph, pw = int(H * 0.16), int(Wd * 0.24)
    for i, (y, x) in enumerate([(0, 0), (0, Wd - pw), (H - ph, 0), (H - ph, Wd - pw)]):
        c = cv2.resize(f0[y:y + ph, x:x + pw], (240, 130)); sheet[rows * hh + 10:rows * hh + 140, i * 250:i * 250 + 240] = c
    cv2.putText(sheet, "corner crops (top-left, top-right, bottom-left, bottom-right): look for logos or watermarks", (10, rows * hh + 148), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(path, sheet)

HUMAN = ["face and outfit match the character sheet (Alex / Mia)", "hands and fingers, jacket zips, watch", "the car is the Shot 1 car (headlights, grille, wing, wheels) in every frame",
         "wheels rotate in the right direction and the car moves along its length", "no weapons that are not in the script (Alex is unarmed in Episode 1)", "no readable text, logos or brand marks appear"]

def verdict(checks):
    s = [c[1] for c in checks]; return "FAIL" if "FAIL" in s else "REVIEW" if "REVIEW" in s else "PASS"

def analyze_clip(path, keyframe=None, need=None, expect=(1920, 1080), outdir=None):
    p = probe(path); frames = sample(path); name = os.path.splitext(os.path.basename(path))[0]; checks = []; extra = {}
    checks.append(("resolution", *check_resolution(p, expect))); checks.append(("frame rate", *check_fps(p)))
    if need is not None:
        ok = p["duration"] >= need - 0.12; checks.append(("duration", "PASS" if ok else "FAIL", f"{p['duration']:.2f} s (need {need:.2f} s)"))
    fz, total = check_freeze(path); checks.append(("frozen frames", *fz))
    st, msg, m = check_motion(frames); checks.append(("real motion", st, msg)); extra["motion"] = m
    st, msg, m = check_watermark(frames); checks.append(("watermark", st, msg)); extra["watermark"] = m
    st, msg, m = check_keyframe(frames, keyframe); checks.append(("starts from keyframe / no glitches", st, msg)); extra["keyframe"] = m
    if outdir: os.makedirs(outdir, exist_ok=True); contact_sheet(frames, os.path.join(outdir, name + "_contact.png"))
    return dict(file=path, probe=p, checks=checks, verdict=verdict(checks), metrics=extra, human_review=HUMAN)

def analyze_final(path, outdir=None, expect=(1920, 1080), ignore=(), still_seconds=0.0, allow_black=()):
    p = probe(path); frames = sample(path, 0.5); checks = []
    checks.append(("resolution", "PASS" if (p["width"], p["height"]) == tuple(expect) else "FAIL", f"{p['width']}x{p['height']}"))
    checks.append(("frame rate", *check_fps(p)))
    checks.append(("duration 30 to 45 s", "PASS" if 30 <= p["duration"] <= 45 else "FAIL", f"{p['duration']:.2f} s"))
    checks.append(("codecs", "PASS" if (p["vcodec"], p["acodec"]) == ("h264", "aac") else "FAIL", f"video {p['vcodec']}, audio {p['acodec']}"))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    try:
        I = float(r.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0]); P = float(r.split("True peak:")[1].split("Peak:")[1].split("dBFS")[0])
        checks.append(("loudness", "PASS" if -20 <= I <= -12 and P <= -1.0 else "REVIEW", f"{I:.1f} LUFS, true peak {P:.1f} dBFS"))
    except Exception: checks.append(("loudness", "REVIEW", "could not be measured"))
    fz, total = check_freeze(path)
    if still_seconds:
        ok = total <= still_seconds + 1.5   # less frozen than declared is fine (fades move); more means an unexpected freeze
        checks.append(("frozen frames", "REVIEW" if ok else "FAIL", f"{total:.1f} s frozen; {still_seconds:.1f} s of of declared static frames (title cards or stills) are in the config" + ("" if ok else ": more frozen video than declared, so something else is frozen")))
    else: checks.append(("frozen frames", *fz))
    st, msg, m = check_motion(frames); checks.append(("real motion", st, msg))
    st, msg, m2 = check_watermark(frames, ignore); checks.append(("watermark", st, msg))
    bl = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "blackdetect=d=0.2:pic_th=0.98", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    mid = [l for l in bl.splitlines() if "black_start" in l and float(l.split("black_start:")[1].split()[0]) < p["duration"] - 0.5 and not any(a - 0.4 <= float(l.split("black_start:")[1].split()[0]) <= b + 0.4 for a, b in allow_black)]
    checks.append(("unexpected black frames", "PASS" if not mid else "REVIEW", "none before the final cut" if not mid else "black section(s) inside the film"))
    if outdir: os.makedirs(outdir, exist_ok=True); contact_sheet(frames, os.path.join(outdir, "final_contact.png"))
    return dict(file=path, probe=p, checks=checks, verdict=verdict(checks), metrics=dict(motion=m, watermark=m2), human_review=HUMAN + ["voices clearly audible and in sync with the picture", "no clipped or distorted audio"])

def to_md(rep):
    lines = [f"### {os.path.basename(rep['file'])}: **{rep['verdict']}**", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {d} |" for n, s, d in rep["checks"]]
    lines += ["", "Needs human review (not automated): " + "; ".join(rep["human_review"]), ""]
    return "\n".join(lines)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["clip", "final"]); ap.add_argument("path"); ap.add_argument("--keyframe"); ap.add_argument("--need", type=float)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "final", "qc")); ap.add_argument("--ignore-corner", action="append", default=[]); ap.add_argument("--still-seconds", type=float, default=0.0); ap.add_argument("--allow-black", action="append", default=[], help="start-end seconds of a title card, e.g. 0-3")
    a = ap.parse_args()
    rep = analyze_clip(a.path, a.keyframe, a.need, outdir=a.out) if a.mode == "clip" else analyze_final(a.path, outdir=a.out, ignore=tuple(a.ignore_corner), still_seconds=a.still_seconds, allow_black=tuple(tuple(float(x) for x in w.split("-")) for w in a.allow_black))
    os.makedirs(a.out, exist_ok=True); base = os.path.splitext(os.path.basename(a.path))[0]
    json.dump(rep, open(os.path.join(a.out, base + "_qc.json"), "w"), indent=1); open(os.path.join(a.out, base + "_qc.md"), "w").write(to_md(rep))
    print(to_md(rep)); sys.exit(0 if rep["verdict"] != "FAIL" else 2)
