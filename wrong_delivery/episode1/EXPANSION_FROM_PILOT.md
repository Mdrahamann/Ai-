# Expanding the pilot to the 8-minute Episode 1

The shot list, screenplay and cost estimates are in `EPISODE1_SCREENPLAY.md`, `episode1_shot_list.csv` and `ANIMATION_PLAN.md` (65 shots, exactly 480 s, 63 AI clips). This page updates that plan with what the six Flow clips taught us.

## Where the six clips fit
| Flow clip | Fills slot in the 65-shot plan | Status |
|---|---|---|
| 01 coastal chase | 1.01 / 1.04 | usable for a pilot only (brand badge, wrong car); replace |
| 02 handoff | 3.06 | **keep** (best clip; native 1080p) |
| 03 dock | 5.05 / 5.06 | **reject**, regenerate with Alex as the start image |
| 04 discovery | 6.03 / 6.04 | **keep** |
| 05 alley run | 7.06 | usable with 0.3 s cut; rifles too close, regenerate if possible |
| 06 office | 8.07 / 8.08 | **keep**, but the sky is a sunset, not a peach dawn |
So **3 of 63 clips are solid, 2 usable with flags, 1 rejected**. About **58 to 60 clips remain**, plus their start images.

## Lessons to apply to every remaining clip (these cause most failures)
1. **Always give Alex and Mia as start or reference images.** Shot 03 failed because a text-only description produced a generic man.
2. **Write "no logos, no badges, no license plate text"** in every car prompt. Shot 01 shows a brand badge.
3. **Describe pursuers as "distant silhouettes with flashlights, no weapons visible"** and say they are far behind.
4. **Ask for 1080p if the tool offers it.** Shot 02 came out at 1080p; the others at 720p. Check the export setting in Flow.
5. **Keep one slow movement per clip and 6 to 8 seconds.** Clips with a static camera and small movements (shots 04 and 06) were cleanest. Fast hands (shots 02 and 04) and body-on-car contact (shot 05) produced the glitches.
6. **Lock the car first.** The car changed in every shot. Generate the car turnaround and use it as a reference in all 21 car shots.

## Production order (gates)
1. **Car and character references:** car sheet from the Shot 1 image; Foreman and pursuer references.
2. **Re-do the three weak slots** (5.05/5.06 dock, 1.01 chase, 7.06 alley) with those references.
3. **Scene by scene** following `ANIMATION_PLAN.md`: hardest car shots first within a scene, check each clip with `qc.py`, keep or retake, and don't start the next scene until it passes.
4. **Assemble** with `timeline.py`, mix with the existing voices (new Foreman voice needed), then run the final check.
5. **Release gates:** no brand badges, no readable plates, a synthetic-content disclosure on YouTube, and a clean 1080p export.

## Footage and cost still needed
About 58 to 60 new clips (about 430 s), at the planning estimates in `ANIMATION_PLAN.md` (roughly 1,500 Higgsfield-standard credits or 5,000 Runway credits for the whole episode). I don't know Google Flow's pricing, so I can't convert your Flow usage to those numbers. Nothing has been bought, and none of this runs without your approval.
