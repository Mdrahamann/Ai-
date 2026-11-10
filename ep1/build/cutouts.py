"""Cut each pose out of the character sheets onto a transparent background."""
import os, numpy as np
from collections import deque
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, "..", "assets"); OUT = os.path.join(HERE, "cutouts")
os.makedirs(OUT, exist_ok=True)
BOXES = {
 "milo_sheet.webp": {"milo_front": (30,40,375,690), "milo_side": (390,40,690,690), "milo_back": (710,40,1020,690),
                     "milo_happy": (1060,30,1300,258), "milo_surprised": (1035,262,1325,476), "milo_worried": (1050,480,1300,718)},
 "pip_sheet.webp": {"pip_front": (150,5,390,375), "pip_side": (580,5,780,375), "pip_back": (990,5,1210,375),
                    "pip_happy": (150,380,390,740), "pip_tilt": (540,380,790,740), "pip_worried": (970,410,1230,740)},
}
def cut(im):
    a = np.asarray(im.convert("RGB")).astype(int); h, w, _ = a.shape
    sat = a.max(2) - a.min(2); lum = a.mean(2)
    bgish = (sat < 14) & (lum > 175)          # light neutral gray = background or soft shadow
    mask = np.zeros((h, w), bool); q = deque()
    for x in range(w):
        for y in (0, h-1): q.append((y, x))
    for y in range(h):
        for x in (0, w-1): q.append((y, x))
    while q:
        y, x = q.popleft()
        if 0 <= y < h and 0 <= x < w and not mask[y, x] and bgish[y, x]:
            mask[y, x] = True; q.extend(((y+1,x),(y-1,x),(y,x+1),(y,x-1)))
    alpha = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA"); out.putalpha(alpha)
    return out.crop(out.getbbox())
for sheet, boxes in BOXES.items():
    im = Image.open(os.path.join(A, sheet))
    for name, box in boxes.items():
        c = cut(im.crop(box)); c.save(os.path.join(OUT, name + ".png")); print(name, c.size)
