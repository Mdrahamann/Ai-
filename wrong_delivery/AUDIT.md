# The Wrong Delivery, Episode 1: file audit and first two clip prompts

Source: `The_Wrong_Delivery_Claude_Production_Pack.zip` (not copied into the repo; the images stay in your zip). `manifest.json` lists every asset and shot.

## 1. What is in the pack (all checked)
| Item | Result |
|---|---|
| 2 character sheets (Alex, Mia) | Open fine, 1448×1086 (4:3). Each has front, three-quarter, side and a close-up portrait. |
| 6 storyboard keyframes | Open fine, 1672×941 (16:9). Match the shot list one to one. |
| Script, shot list, visual bible, master prompt, assets.json | All consistent with each other. |
| 42 s silent animatic | H.264, 42.0 s, 24 fps, but **1280×720** (not the 1080p target) and **moving stills only**. |

## 2. Continuity problems found in the keyframes
1. **The car changes between shots.** Shot 1 has a blade-shaped LED headlight, a mesh grille and a rear wing. Shot 3 has round twin projector lamps with a curved LED strip and no wing. The visual bible already warns about this. **Shot 1 should be the canonical car**; shots 3 and 5 need re-generating with it as a reference before any clip uses them. Video from a mismatched keyframe will lock the wrong car in.
2. **Shot 5: Alex runs holding a pistol, and the pursuers are close and carry rifles.** The script says "armed pursuers far behind" and the bible says Alex is "not cartoonishly aggressive". Decide whether Alex is armed. It also matters for YouTube's rules on violent content.
3. **Shot 6 is a sunset-style purple/orange sky, not the "muted peach dawn"** the bible describes.
4. **Props and hands look fine.** The brown box (S03), the dark case with blue glow (S04) and Alex's watch are consistent, and the hand in S04 has five fingers. Check again on the generated motion clips, which is where hands and wheels usually break.
5. The nightclub name, Pier 19 and the city (Caldera Bay) are all original. No Rockstar or GTA logos are visible in the keyframes.

## 3. What I can and can't do in this session
| Need | Status |
|---|---|
| FFmpeg, Python, Kokoro voices (Alex/Mia), music and sound effects | **Available now, free.** I can build the voices, mix and subtitles. |
| Real motion (cars driving, people moving) | **Not possible for free.** Your Higgsfield balance is **5.6 credits** (free plan). Image-to-video with Kling 3.0 costs **9 credits for 6 s (standard) or 10.5 (pro)**, so I can't afford even one clip. |
| Downloading finished clips | This session's proxy blocked Higgsfield's file server earlier. A paid plan alone wouldn't be enough; I'd also need that host allowed. |

**Cost to animate the 42 s pilot (6 clips):** about 54 credits (standard) or 63 (pro) if every clip works first time. Plan for 2× that for re-generations, so roughly **110–125 credits**. Your master prompt says you don't want to buy more subscriptions yet, so the choices are:
- **A. Free animatic:** I improve the existing stills with camera moves, rain and light effects, voices, music and subtitles, clearly labelled as an animatic (not AI character animation).
- **B. Free tiers elsewhere:** you run the six clip prompts yourself in any image-to-video tool you can access (I haven't verified any tool's current free limits) and send me the clips; I mix them with the voices.
- **C. Pay for credits** on Higgsfield (or similar), and I run the clips.

## 4. First two image-to-video prompts
Use the keyframe as the **start image** (Kling 3.0 takes a start image, not extra reference images, so the keyframe itself carries the identity). Settings for both: 16:9, 6 s, sound off, no watermark. Voices and sound go on separate tracks.

**Shot 01, Car chase** (start image: `SHOT_01_CAR_CHASE.png`)
```
Keep the exact scene, black coupe, driver and lighting of the first frame. Slow low tracking shot following the car along the rainy neon waterfront road. The car drives forward steadily; water sprays backward from the tires; the wheels rotate naturally; red and blue police light reflections slide across the wet asphalt; rain falls. The driver looks ahead, hands on the wheel, face unchanged. The police car stays in the background behind. No new objects, no text, no logos, no change to the car's shape, headlights or rear wing. Photorealistic, cinematic, 24 fps.
```
Negative prompt (if the tool has one): `deformed car, changing car shape, melting wheels, extra fingers, face change, text, logo, watermark`

**Shot 02, Nightclub handoff** (start image: `SHOT_02_NIGHTCLUB_HANDOFF.png`)
```
Keep the exact scene, characters, outfits and lighting of the first frame. Subtle slow dolly in over Mia's shoulder toward Alex. Mia holds out the flat dark envelope once; Alex takes it naturally with his right hand. Mia's long hair and the rain move gently. In the background the crowd and velvet ropes barely move and the magenta nightclub sign stays steady. Faces, outfits, gold earrings, leather jacket and silver watch unchanged. Only one envelope, no other objects handed over, no text, no logos. Photorealistic, cinematic, 24 fps.
```
Negative prompt: `extra hands, extra fingers, face change, outfit change, second envelope, text, logo, watermark, fast motion`

**Quality check on each clip (do before using it):** car shape and wheel rotation, hands and fingers, faces versus the character sheets, signage, then fix or regenerate.

## 5. Voices (ready to produce)
Kokoro is installed here. Planned voices: Alex `am_michael` (lowered slightly, calm), Mia `af_nicole` (steady, low). One WAV per line with 0.3 s of head and tail. Check the licence of the Kokoro voice files for the distribution you plan before monetising; I haven't verified it for this use.

## 6. Disclosure
These are realistic synthetic scenes. Turn on YouTube's "altered or synthetic content" disclosure when uploading.
