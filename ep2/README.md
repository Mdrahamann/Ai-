# Episode 2: Milo and the Windy Day

**Watch:** `ep2_milo_and_the_windy_day.mp4` (6:00, 1920x1080, 24 fps, with voices, music, sound effects and captions)

| File | What it is |
|---|---|
| `ep2_milo_and_the_windy_day.mp4` | The finished episode |
| `ep2_captions.srt` | Closed captions for YouTube |
| `production_package.md` | Script, timeline, AI video prompts, YouTube copy, future episode ideas |
| `plan.py` | Single source for every shot, line and cue. Run it to rebuild the package and recheck the timing. |
| `shots.csv` | The timeline as a spreadsheet |
| `build/` | Rebuilds the video: `audio.py` (voices, music, SFX), `render.py` (pictures), `preview.py` (contact sheet), `synth.py` (shared sound kit) |

**How it was made:** this is a cartoon cut, not AI video. Milo and Pip are the pose cutouts from the Episode 1 reference sheets (`ep1/build/cutouts`). The porch, the craft corner, the paper windmill (with its rip, bigger rip and rainbow patch), the wind lines, the caption pills, the thought bubble and the "!" icon are all drawn in code. Characters bob while they speak, puff up when frustrated and swell with each breath; there is no lip-sync. The timings come straight from `plan.py`, so any AI clips generated later from the prompts drop in at the same timecodes.

**Sound:** the voices use Kokoro TTS with the same settings as Episode 1. The wind is one fixed recording used at 0:00, at 1:10 (quieter) and again at 5:11, when it spins the mended windmill instead of tearing it. Three soft chimes play under each "Pause. Breathe. Tell me." The music cuts out at both rips and during the quiet moment. The mix is normalized to -15 LUFS.

## Rebuild
```bash
pip install kokoro-onnx soundfile numpy pillow    # plus ffmpeg
cd build
KOKORO_DIR=/path/to/kokoro python3 audio.py      # needs kokoro-v1.0.int8.onnx + voices-v1.0.bin
python3 render.py                                 # or: python3 render.py S14 S15 && REUSE=1 python3 render.py
```
