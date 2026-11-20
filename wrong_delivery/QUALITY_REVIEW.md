# Quality review of the six Google Flow clips (Shots 01 to 06)

Reviewed 2026-11-20 frame by frame at 0.5 s steps, plus full-resolution crops of every suspect spot and a per-frame jump check. Originals are untouched (working copies in `clips/` match your uploads byte for byte).

## Decisions
| Shot | File | Native | Decision | Segment used in the pilot |
|---|---|---|---|---|
| 01 | Sports coupe accelerating | 1280x720, 8.04 s | **TRIM + FLAG** | 0.00 to 4.00 s |
| 02 | Characters exchanging envelope | **1920x1080**, 7.85 s | **TRIM** (strongest shot) | 0.00 to 5.30 s |
| 03 | Delivery driver holding package | 1280x720, 7.93 s | **REJECT** (wrong man) | not used in the pilot (review cut only, 0.8 to 5.8 s) |
| 04 | Driver opening glowing case | 1280x720, 7.93 s | **PASS** | 0.20 to 6.80 s |
| 05 | Man running through neon alley | 1280x720, 7.93 s | **TRIM + FLAG** | 0.30 to 7.10 s |
| 06 | Characters facing across office | 1280x720, 7.93 s | **PASS + FLAG** | 0.00 to 7.00 s, colour-graded |

## Serious problems, with timestamps
**Shot 01**
- **4.05 to ~5.5 s:** a white blob appears beside the right headlight, grows, drifts and fades. Cut out (clip ends at 4.00 s).
- **Whole clip, unfixable:** a winged brand badge sits on the grille (clear at 1.0 s and 4.5 s). The car is a different grand tourer from our master car, the driver is tiny, and the location is a coastal dusk road, not the neon waterfront.

**Shot 02**
- **5.33 s:** an abrupt jump (frame similarity drops to 0.73); the envelope changes from a flat card to a black triangle between about 5.0 and 5.5 s. Cut out (clip ends at 5.30 s). Later, around 7.0 s, Mia's hand makes an odd shape.
- **Whole clip, unfixable (background):** the car Alex leans on is an unreadable shiny blob.
- **Good:** Alex and Mia match their character sheets (jacket, watch, blouse, blazer, hoops) throughout. The handoff reads clearly.

**Shot 03**
- **Whole clip:** the man is **not Alex** (blue puffer jacket, different face and hair). A green delivery bag appears behind his shoulder from about 2.5 s. The car in profile is not the master car (no wing, different body). He stands almost still, touching his collar. A different man under Alex's voice-over breaks the story, so it is **rejected**. It could not be fixed by trimming.

**Shot 04**
- **~6.8 to 7.4 s:** the left hand's fingers go blurry and spectral in the blue light. Trimmed at 6.80 s. A slight face change between 0 to 3.5 s and 4.5 s onward is minor.
- Alex is consistent with his sheet, and the interior matches the storyboard.

**Shot 05**
- **0.00 to 0.08 s:** Alex holds a **black handgun** in his right hand; by 0.17 s the hand is empty. Cut out (clip starts at 0.30 s). Alex is unarmed in Episode 1.
- **Whole clip, unfixable:** three or four pursuers with **rifles** run 3 to 6 m behind him, not "far behind" with weapons lowered.
- **6.4 to 7.8 s:** he bends awkwardly over the trunk; a license plate is partly visible. Clip ends at 7.10 s.

**Shot 06**
- **Whole clip, unfixable:** the sky is a purple and orange **sunset**, not the muted peach dawn. A grade removes much of the magenta and purple, but it still reads as a low sun at the horizon.
- Characters match their sheets; motion is subtle (static camera).

## Across the clips, not fixable by editing
- **The car is different in every car shot** (shot 01 front, shot 03 profile, shot 05 rear). None is the permanent Shot 1 car.
- **Shot 01's brand badge** makes the pilot unsuitable for public release as is.
- Four of six clips are native 720p. They are scaled to 1080p; scaling adds no detail.
- Shots 03's replacement does not exist, so the story skips the dock pickup.

## What I did in the edit
- Trimmed as above; hard cuts; opening and ending title cards with fades; a half-second fade out of shot 06 into the end card.
- Voices: the existing Kokoro Alex and Mia. The shot 01 voice-over runs 0.25 s over the cut, which is normal practice. The line about "that box" moves under shot 04 because shot 03 is out.
- Sound: synthesized rain, engine, tire spray, sirens, helicopter, footsteps, club bass, latch, electronic pulse, an original music bed and a rising sting. The clips' own built-in audio was not used (I can't listen to it).
- Colour: only shot 06 was graded. I did not colour-match the others; they differ in look.

## Rebuild
```bash
cd wrong_delivery/build
export KOKORO_DIR=/path/to/kokoro
PILOT=pilot_cinematic.json AUDIO_OUT=$PWD/out_cinematic python3 audio.py
PILOT=pilot_cinematic.json python3 timeline.py --audio out_cinematic/mix.wav --srt out_cinematic/pilot.srt --out ../final/the_wrong_delivery_CINEMATIC_PILOT.mp4
python3 qc.py final ../final/the_wrong_delivery_CINEMATIC_PILOT.mp4 --still-seconds 7 --allow-black 0-3 --allow-black 32.7-36.7
```
(`pilot_review_all6.json` builds the all-six review cut with the flags on screen.)
