"""Assemble the pilot from real generated clips + the audio mix. Re-runnable; every problem is reported before anything is rendered.

  python3 timeline.py                      # uses ../pilot.json, ../clips/shotNN.mp4, out/mix.wav, ../pack/ keyframes
  python3 timeline.py --subtitles          # burn in legible subtitles
  python3 timeline.py --clips DIR --pack DIR --out FILE

Rules (on purpose):
 * No still-image fallback. A missing clip, a clip that is too short, or a clip that fails the quality check stops the build.
   (A clip may be up to 0.12 s short: the last frame is held for that fraction of a second, and it is logged.)
 * Clips that FAIL qc (no real motion, watermark, wrong start frame, frozen video) are refused. With --allow-flagged the film is still
   built, but only as <name>_FLAGGED_NOT_FINAL.mp4 so it can never be mistaken for a finished export.
 * Clips below 1920x1080 are scaled up with a warning; that is not native 1080p and is recorded in final/build_log.json.
 * The output is H.264 1080p 24 fps + AAC, with no watermark added by us.
"""
import os, sys, json, hashlib, argparse, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import qc

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", default=os.path.join(ROOT, "clips")); ap.add_argument("--pack", default=os.path.join(ROOT, "pack"))
    ap.add_argument("--pilot", default=os.path.join(ROOT, os.environ.get("PILOT", "pilot.json"))); ap.add_argument("--audio", default=os.path.join(HERE, "out", "mix.wav"))
    ap.add_argument("--out", default=os.path.join(ROOT, "final", "the_wrong_delivery_pilot.mp4")); ap.add_argument("--subtitles", action="store_true")
    ap.add_argument("--srt", default=os.path.join(HERE, "out", "pilot.srt")); ap.add_argument("--allow-flagged", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.pilot)); W, H = cfg["size"]; FPS = cfg["fps"]; shots = cfg["shots"]
    total = sum(s["dur"] for s in shots); problems = []; warnings = []; reports = {}; log = dict(shots=[])
    if not os.path.exists(a.audio): problems.append(f"audio mix not found: {a.audio} (run audio.py first)")
    for s in shots:
        clip = os.path.join(a.clips, os.path.basename(s["clip"]))
        if not os.path.exists(clip): problems.append(f"shot {s['id']}: clip missing: {clip}. No substitute is used; generate this clip."); continue
        kf = os.path.join(a.pack, s.get("keyframe", "")); kf = kf if os.path.exists(kf) else None
        try: rep = qc.analyze_clip(clip, kf, s["dur"], (W, H), outdir=os.path.join(ROOT, "final", "qc"))
        except Exception as e: problems.append(f"shot {s['id']}: cannot read clip ({e})"); continue
        reports[s["id"]] = rep
        for n, st, d in rep["checks"]:
            if st == "FAIL": (warnings if a.allow_flagged else problems).append(f"shot {s['id']}: {n}: {d}")
            elif st == "REVIEW": warnings.append(f"shot {s['id']}: {n}: {d}")
        log["shots"].append(dict(id=s["id"], clip=clip, sha256=sha(clip), probe=rep["probe"], qc=rep["verdict"]))
    if problems:
        print("BUILD STOPPED. Fix these first:"); [print("  -", p) for p in problems]; return 1
    flagged = any(r["verdict"] == "FAIL" for r in reports.values())
    out = a.out
    if flagged: out = os.path.splitext(out)[0] + "_FLAGGED_NOT_FINAL.mp4"
    inputs = []; chains = []; labels = []
    for i, s in enumerate(shots):
        clip = os.path.join(a.clips, os.path.basename(s["clip"])); inputs += ["-i", clip]; p = reports[s["id"]]["probe"]
        pad = max(0.0, s["dur"] - p["duration"])
        if pad > 0: warnings.append(f"shot {s['id']}: clip is {pad:.2f} s short; last frame held for {pad:.2f} s")
        if (p["width"], p["height"]) != (W, H): warnings.append(f"shot {s['id']}: native {p['width']}x{p['height']} scaled to {W}x{H} (not native 1080p)")
        f = f"[{i}:v]fps={FPS},"
        if pad > 0: f += f"tpad=stop_mode=clone:stop_duration={pad:.3f},"
        f += f"trim=duration={s['dur']},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"
        chains.append(f); labels.append(f"[v{i}]")
    chains.append("".join(labels) + f"concat=n={len(shots)}:v=1:a=0[vc]")
    last = "[vc]"
    if a.subtitles or cfg.get("subtitles_default"):
        srt = os.path.relpath(a.srt).replace("\\", "/").replace(":", "\\:")
        chains.append(f"[vc]subtitles='{srt}':force_style='FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=48'[vs]"); last = "[vs]"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-loglevel", "error", "-y"] + inputs + ["-i", a.audio, "-filter_complex", ";".join(chains), "-map", last, "-map", f"{len(shots)}:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
    print("rendering", out); r = subprocess.run(cmd)
    if r.returncode: print("ffmpeg failed"); return 1
    log.update(output=out, output_sha256=sha(out), total_seconds=total, flagged=flagged, warnings=warnings, audio_sha256=sha(a.audio), pilot=a.pilot,
               ffmpeg=subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0])
    json.dump(log, open(os.path.join(ROOT, "final", "build_log.json"), "w"), indent=1)
    for w in warnings: print("  warning:", w)
    print("built:", out, "(FLAGGED, NOT FINAL)" if flagged else "(now run: python3 qc.py final " + out + ")")
    return 0

if __name__ == "__main__": sys.exit(main())
