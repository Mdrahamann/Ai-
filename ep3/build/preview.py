"""Contact sheet, one frame per shot at the given fraction: python3 preview.py out.png [frac] [S01 S02 ...]"""
import sys
from PIL import Image, ImageDraw
import render as R
out = sys.argv[1]; frac = float(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("S") else 0.6
ids = [a for a in sys.argv[2:] if a.startswith("S")] or [s["id"] for s in R.plan.SHOTS]
tiles = []
for sid in ids:
    s = R.SH[sid]; d = s["dur"]; t = d * frac
    im = R.build(sid).frame(t, d, s["start"] + t).convert("RGB").resize((480, 270))
    ImageDraw.Draw(im).text((8, 6), sid, fill=(0, 0, 0)); tiles.append(im)
cols = 4; sheet = Image.new("RGB", (cols * 480, ((len(tiles) + cols - 1) // cols) * 270), "white")
for i, im in enumerate(tiles): sheet.paste(im, ((i % cols) * 480, (i // cols) * 270))
sheet.save(out)
