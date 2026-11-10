"""Build a timed 6:00 animatic (placeholder per shot) from production_package.md.
Usage: python3 make_animatic.py  -> writes animatic.mp4 + shots.csv next to this script.
Swap each placeholder for the generated clip of the same shot ID when available."""
import re, csv, os, subprocess, tempfile, textwrap
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "production_package.md"), encoding="utf-8").read()
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def t(s):
    m, s = s.split(":"); return int(m) * 60 + int(s)

rows = []
for line in src.splitlines():
    p = line.split("\t")
    if len(p) >= 7 and re.fullmatch(r"S\d\d", p[0]):
        rows.append(dict(shot=p[0], start=t(p[1]), end=t(p[2]), action=p[4], line=p[5], sound=p[6]))
assert rows and rows[-1]["end"] == 360, "timeline should end at 6:00"
for a, b in zip(rows, rows[1:]):
    assert a["end"] == b["start"], (a["shot"], b["shot"])

with open(os.path.join(HERE, "shots.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

PALETTE = [(255,214,214),(255,229,204),(255,247,204),(214,245,214),(204,229,255),(229,214,255)]
tmp = tempfile.mkdtemp()
f_big, f_mid, f_small = ImageFont.truetype(BOLD, 64), ImageFont.truetype(FONT, 40), ImageFont.truetype(FONT, 30)
listfile = os.path.join(tmp, "list.txt")
with open(listfile, "w") as L:
    for i, r in enumerate(rows):
        img = Image.new("RGB", (1920, 1080), PALETTE[i % 6]); d = ImageDraw.Draw(img)
        mm = lambda s: f"{s//60}:{s%60:02d}"
        d.text((80, 60), f"{r['shot']}   {mm(r['start'])}-{mm(r['end'])}  ({r['end']-r['start']} s)", font=f_big, fill=(60,60,90))
        y = 200
        for ln in textwrap.wrap("ACTION: " + r["action"], 70):
            d.text((80, y), ln, font=f_mid, fill=(40,40,40)); y += 52
        y += 30
        for ln in textwrap.wrap("SOUND: " + r["sound"], 90):
            d.text((80, y), ln, font=f_small, fill=(90,90,90)); y += 40
        dl = r["line"]
        if not dl.startswith("(silence"):
            box_y = 800
            d.rounded_rectangle((60, box_y, 1860, 1030), 30, fill=(255,255,255))
            yy = box_y + 30
            for ln in textwrap.wrap(dl, 60)[:4]:
                d.text((100, yy), ln, font=f_mid, fill=(20,20,20)); yy += 50
        png = os.path.join(tmp, f"{r['shot']}.png"); img.save(png)
        L.write(f"file '{png}'\nduration {r['end']-r['start']}\n")
    L.write(f"file '{png}'\n")
out = os.path.join(HERE, "animatic.mp4")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",listfile,
                "-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","360",
                "-vf","fps=24,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","28",
                "-c:a","aac","-shortest",out], check=True)
print(out, len(rows), "shots")
