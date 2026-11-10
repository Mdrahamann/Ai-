# Episode 1: Milo and the Missing Rainbow Color

**Watch:** `ep1_milo_and_the_missing_rainbow_color.mp4` (6:00, 1920x1080, 24 fps, with voices, music and sound effects)

This cut is built from the two character reference sheets. Each shot is a drawn set (garden, tulips, pond,
sunflowers, fence end, sky, clue cards) with Milo and Pip cut out of the sheets. They hop, wobble and bob
while they talk; there is no lip-sync. When AI video clips for a shot are generated later, drop them over
the same timecodes: the soundtrack stays the same.

| File | What it is |
|---|---|
| `ep1_milo_and_the_missing_rainbow_color.mp4` | The finished episode |
| `ep1_captions.srt` | Closed captions for YouTube |
| `production_package.md` | Plan, character prompts, script, timeline, 52 shot prompts, YouTube assets. The reuse lines now match the sheets. |
| `shots.csv` | The editing timeline as a spreadsheet |
| `animatic.mp4` | The silent timing guide (one card per shot) |
| `assets/milo_sheet.webp`, `assets/pip_sheet.webp` | Character reference sheets (Higgsfield jobs `76f7f758-…`, `fdacf664-…`) |
| `build/` | Everything needed to rebuild the episode |

## Sound
- **Voices:** Kokoro TTS (open model, runs locally). Milo = `af_sky` raised 3 semitones, Pip = `af_heart` raised 1 semitone, Narrator = `bf_emma`, all slowed for preschool pace. Includes giggles, the sneeze, "Hup!" and cheers.
- **Music:** synthesized in `build/audio.py`: a theme melody plus moods per section (intro, travel, tick-tock under the three viewer questions, magical swell, outro with a 3 s fade). It ducks under dialogue.
- **SFX:** synthesized to follow the Sound column (splash, boing, tings on each color word, sparkles, whoosh, whirring pinwheel, click, and more).
- Mix normalized to -15 LUFS.

## Rebuild
```bash
pip install kokoro-onnx soundfile numpy pillow   # plus ffmpeg
# download kokoro-v1.0.int8.onnx and voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0)
cd build
python3 cutouts.py
KOKORO_DIR=/path/to/kokoro python3 audio.py
python3 render.py            # full render; to redo a few shots: python3 render.py S14 S15 && REUSE=1 python3 render.py
python3 preview.py sheet.png # contact sheet, one frame per shot
```
