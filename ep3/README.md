# Episode 3: Milo and the Missing Cookie

**Watch:** `ep3_milo_and_the_missing_cookie.mp4` (6:00, 1920x1080, 24 fps, with voices, music, sound effects and captions)

**Feeling:** guilt. **Takeaway:** when you make a mistake, telling the truth is brave, and it makes the heavy feeling go away.
**New character:** Mr. Bumble, the kind neighbor (from `characters/mr_bumble_suspenders.jpg`).

| File | What it is |
|---|---|
| `ep3_milo_and_the_missing_cookie.mp4` | The finished episode |
| `ep3_captions.srt` | Closed captions for YouTube |
| `production_package.md` | Script, timeline, AI video prompts, YouTube copy |
| `plan.py` | Single source for every shot, line and cue. Run it to rebuild the package and recheck the timing. |
| `shots.csv` | The timeline as a spreadsheet |
| `build/` | `audio.py` (voices, music, SFX), `render.py` (pictures), `preview.py` (contact sheet), `synth.py` (shared sound kit), `cutouts/bumble_front.png` |

**How it was made:** this is the same cutout cartoon method as Episodes 1–2. Milo and Pip use the poses cut from the Episode 1 sheets. Mr. Bumble is cut from the supplied image, which has one front pose, so he leans, sits, kneels and bobs rather than turning. The kitchen has cool blue walls so the three yellow characters stand out. The cookie tray, flour puffs, crumbs, icing dots and caption pills are drawn in code. When Milo feels guilty, his body sinks and cools in color; when he tells the truth, it lifts and warms again. There is no lip-sync.

**Voices:** the same as Episodes 1–2, plus Mr. Bumble (Kokoro `am_michael`, lowered 1.5 semitones, slow and warm).

## Rebuild
```bash
pip install kokoro-onnx soundfile numpy pillow    # plus ffmpeg
cd build
KOKORO_DIR=/path/to/kokoro python3 audio.py
python3 render.py                                 # or: python3 render.py S14 S15 && REUSE=1 python3 render.py
```
