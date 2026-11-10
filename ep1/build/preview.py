"""Contact sheet of one frame per shot (at 60% of each shot) for a quick visual check."""
import sys, os
from PIL import Image, ImageDraw
import render as R
shots = sys.argv[2:] or [s["shot"] for s in R.shots]
tiles = []
for sh in shots:
    s = R.SH[sh]; d = s["end"] - s["start"]; t = d * 0.6
    sc = R.build(sh)
    if sc == "title": im = list(R.title_frames(int(t * R.FPS) + 1))[-1]
    elif sc == "end": im = next(R.end_frames(1))
    else: im = sc.frame(t, d, s["start"] + t).convert("RGB")
    im = im.resize((480, 270)); ImageDraw.Draw(im).text((8, 6), sh, fill=(0, 0, 0)); tiles.append(im)
cols = 4; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 480, rows * 270), "white")
for i, im in enumerate(tiles): sheet.paste(im, ((i % cols) * 480, (i // cols) * 270))
sheet.save(sys.argv[1])
