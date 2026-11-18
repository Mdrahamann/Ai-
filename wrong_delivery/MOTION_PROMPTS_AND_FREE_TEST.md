# Motion prompts for Shot 1, and the free test

**No money, no paid plans.** If a tool asks for payment or an upgrade at any point, stop and tell me.

## What I could and couldn't verify
I cannot log into your Luma or Runway account from here, so **I cannot run the test myself.** You run it, and I check the result. What I found online (all from third-party sites, not the companies' own pages, so please check what your account screen actually shows):

| | Runway Gen-4 Turbo | Luma Ray3 (Draft mode) |
|---|---|---|
| Free allowance | About 125 one-time credits that do not refill, [per one pricing guide](https://creatify.ai/es/blog/runway-pricing-(2026)-plans-credits-and-what-you-ll-actually-pay) | Sources disagree: from none to roughly 125–500 credits; one says about [8 draft videos a month](https://book.st-hakky.com/en/data-science/luma-ai-dream-machine-ray3-draft-mode-free-to-plus-criteria) |
| Cost per clip | About 5 credits per second, so a 5 s clip is about 25 credits | Draft is said to cost about 60–120 credits for 5–10 s, but sources conflict |
| Image-to-video on free | Yes, Gen-4 Turbo image-to-video | Not confirmed |
| Output | 720p, **with a watermark** on free | Free output generally 720p, **with a watermark** and non-commercial |
| Clip length | 5 s or 10 s | 5 s on free |

What this means:
- **Runway free credits cover only about five 5-second clips.** The six-shot pilot needs six clips plus retries, so free credits alone will not finish the pilot. Combining Luma and Runway may get close.
- **Free clips are 720p and watermarked.** That makes them good for *testing motion quality*, but not for a clean final film. Don't crop, blur or paint out a watermark to hide it. Treat watermarked clips as test footage. If you later want a clean final, that is a paid decision for you to make.
- Free-tier terms change often. Trust the numbers on your own screen over this table.

## The test: one 5-second clip of Shot 1
Shot 1 needs no image correction, so you can start now. Use the original `SHOT_01_CAR_CHASE.png` as the start image.

**Settings (either tool):** image-to-video, start image = Shot 1, 16:9, 5 seconds, lowest cost option, **audio/sound off** if offered, no extras (no upscaling, no "enhance"). Run it **once**. Before you start, take a screenshot of the credits balance, and another after.

### Runway Gen-4 Turbo prompt
Runway's own guidance says the prompt should [describe movement, not re-describe the image](https://help.runwayml.com/hc/en-us/articles/48324313115155-Image-to-Video-Prompting-Guide), so this one is all motion:
```
The black sports car drives forward along the wet road at steady speed. Camera: low tracking shot following alongside the car. Water sprays backward from the tires, the wheels rotate naturally, and rain falls. Red and blue police light reflections slide across the wet asphalt, and the police car stays far behind in the background. The driver keeps both hands on the wheel and looks ahead.
```

### Luma Ray3 Draft prompt
I could not confirm Luma's current prompt guidance, so this keeps the scene brief and the motion explicit:
```
Rainy neon waterfront road at night. The black sports car drives forward at steady speed while a low camera tracks alongside it. Water sprays backward from the tires, the wheels spin naturally, heavy rain falls, and red and blue police light reflections move across the wet asphalt. A police car follows far behind. The driver looks ahead with both hands on the wheel. Realistic motion, photorealistic, cinematic.
```

### If the result looks wrong, change one thing at a time
| Problem | Try |
|---|---|
| Car shape changes or melts | Remove "tracking alongside"; use "camera follows steadily from the front quarter"; shorten the motion description |
| The car barely moves, only the camera does | Add "the car moves clearly forward across the frame" |
| Wheels spin backwards or skid | Remove the wheel sentence; keep spray and rain |
| Driver's face changes | Remove the driver sentence |
| Too much motion or chaos | Add "slow, smooth, minimal motion" |
Avoid: fast turns, drifting, jumps, people running at the camera. They break these models most.

## What to send me
1. The downloaded clip **as-is** (do not edit, crop or re-compress it), as `wrong_delivery/clips/shot01.mp4` or just upload it to me.
2. The tool name, model, mode, duration, and the credits before and after.
3. The exact prompt you used.

I will run the quality check and report: real motion vs camera move on a still, resolution, watermark, whether it starts from the keyframe, glitches, plus a contact sheet I inspect by eye for face, hands, car shape and wheels. A clip passes only if it passes both the automated and the visual check.

## Next shots
After the corrected images are approved, I'll adapt the prompts for Shots 2–6 the same way (motion only for Runway, short scene plus motion for Luma). Keep each clip to one slow, simple movement: dolly in, a person turns, a car drives forward.
