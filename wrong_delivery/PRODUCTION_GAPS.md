# Production gaps (after the first prototype)

Updated 2026-11-19. The prototype is a 33.5 s rough cut. It is **not** the pilot and **not** the episode.

## What the prototype is
`final/the_wrong_delivery_pilot_PROTOTYPE.mp4` (1920x1080, 24 fps, H.264 + AAC, -16.5 LUFS). **14.0 s AI motion** (two clips) and **19.5 s storyboard stills** (labelled on screen). Voices, ambience, engine, rain, sirens, effects and a music bed are mixed under it, with burned-in subtitles.

## Gaps, most important first
| # | Gap | Why it matters | What closes it |
|---|---|---|---|
| 1 | **Only 42% of the prototype is real motion.** The rest are stills. | The goal is a film, not stills with a voice-over. | Real clips for shots 2, 3, 4 and 6 (and the rest of the episode). |
| 2 | **The two AI clips show the wrong cars.** Clip A is a different supercar from the rear (no driver visible, legible license plate). Clip B is a different grand tourer from the front with a **winged brand badge on the grille**. Neither is our Shot 1 car, and they don't match each other. | Continuity. The badge and plate are also a risk for public release. | Replace both with clips made from the approved car sheet. Until then the prototype is for private review only. |
| 3 | **Both AI clips are 1280x720.** The export is scaled to 1080p; scaling adds no detail. | Softer than true 1080p. | Generate at 1080p if a tool offers it; otherwise accept 720p-source softness. |
| 4 | **Clip B is a coastal highway at dusk,** not the neon city of Shot 1; the driver is tiny and not recognisable as Alex. | Location and character continuity. | New clip from the corrected references. |
| 5 | **No corrected Shot 3 file was supplied.** The five inline pictures (4 to 7) are not our characters or car: two strangers in an ornate room, a boxy retro coupe at a dock with visible tire and brand lettering, a man in a suit with a box, a hooded runner in a neon street. | The prototype uses the **original, uncorrected** Shot 3 (car design is wrong; labelled on screen). | Send the corrected Shot 3 file (and the approved car sheet) when you have them. |
| 6 | **Shot 6 still has the purple sunset** (labelled on screen). Shot 5 (original) shows Alex with a pistol and close pursuers, so **it is not used** in the prototype. | Decisions 3 and 4. | The ChatGPT corrections in `IMAGE_CORRECTION_CHECKLIST.md`. |
| 7 | **The clips' own built-in audio was not used.** I can't listen to it, so I replaced it with the synthesized mix. The originals are untouched. | The synthesized engine, rain and sirens are pilot-grade, not cinema-grade. | Replace the effects with licensed library sounds, or tell me to mix the clips' own audio in. |
| 8 | **Voices are generic Kokoro voices** and I have not heard them against picture. They need a listen for pace and emotion. | Performance. | Your review; I will re-time or re-voice any line you flag. |
| 9 | **No mouth movement is possible yet** (the on-screen lines in 3 to 6 are over stills). | Dialogue shots need lip-sync or cutaway coverage. | Plan dialogue as over-the-shoulder, silhouette or cutaway shots (already how the shot list is written). |
| 10 | **No keyframes exist for about 58 of the 63 clips,** and no reference sheets for the Foreman or the pursuers. | Every clip starts from a checked image. | See `episode1/ANIMATION_PLAN.md`. |
| 11 | **Credits:** your Higgsfield balance is 5.6; Runway's free tier covers about five clips with a watermark. | The full episode needs about 1,500 to 5,000 credits (estimate). | Your decision on the paths in the animation plan. Nothing is bought without you. |

## Rules still in force
No purchases or paid APIs. No still-image zooms passed off as animation. No claim that the 8-minute film is made. Kids' channel files are untouched and separate.

## Tool changes made for this build (and why)
- `timeline.py`: a shot can now be explicitly declared a storyboard still (burned-in label, counted separately, never as animation), and AI clips can carry a "prototype" label. A bug that mis-read a missing keyframe as a folder is fixed. It still refuses missing, short or failing clips.
- `qc.py`: the final check can ignore our own label corner and compares the frozen time against the declared stills, so unexpected freezes still fail.
- `audio.py`: the prototype builds into its own folder, shares the voice cache, and a shot can borrow another shot's sound design. The original pilot audio is unchanged.
