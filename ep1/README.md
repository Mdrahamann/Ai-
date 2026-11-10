# Episode 1: Milo and the Missing Rainbow Color

| File | What it is |
|---|---|
| `production_package.md` | The full package: plan, character prompts, script, timeline, 52 shot prompts, YouTube assets |
| `shots.csv` | The editing timeline as a spreadsheet (shot, start, end, action, line, sound) |
| `animatic.mp4` | A 6:00 timing guide with one placeholder card per shot (action, sound, dialogue). Drop each generated clip over its card in the editor. |
| `make_animatic.py` | Rebuilds `shots.csv` and `animatic.mp4` from the package and checks that the timeline covers 0:00 to 6:00 with no gaps |

## Generated so far (Higgsfield, model flux_3_image)
- Milo reference sheet: job `76f7f758-3549-4319-8899-3cd906aee12e`
- Pip reference sheet: job `fdacf664-0626-455b-906f-24f63e0825a3`

Use these job IDs as `start_image` / `image_references` for the video shots so the characters stay consistent.

## Still to do
45 shots need video clips (47 generations). The free plan can't produce them: video models need about 9 to 42 credits per clip and need a paid plan.
