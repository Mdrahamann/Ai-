# Image correction checklist (do this in ChatGPT)

Decisions this checklist enforces:
1. Alex Carter and Mia Reyes look **exactly** like their reference sheets.
2. The black sports car in **Shot 1** is the permanent vehicle. Shots 3 and 5 are corrected to match it.
3. **Alex is unarmed** in Episode 1. The pistol is removed from Shot 5 and the pursuers are much further back.
4. Shot 6 is a **muted peach dawn**, not a purple sunset.

Shots **1, 2 and 4 need no edits** (check them against the table at the end). Shot 1 is already approved, so you can start the motion test with it now.

## How to work (this keeps faces and cars from drifting)
- **One image per chat.** Start a new ChatGPT chat for each correction. Long chats drift.
- In each chat attach: both character sheets (`CHAR_ALEX_CARTER.png`, `CHAR_MIA_REYES.png`), `SHOT_01_CAR_CHASE.png`, `ref/CAR_REFERENCE_from_SHOT_01.png`, and **the image being edited**.
- Use the edit prompts below as written. They list what must stay unchanged; models obey "change only X" better than "make it better".
- Ask for **16:9, at least 1920×1080** if the tool lets you. Otherwise keep the original 1672×941 and tell me.
- If a result changes a face, outfit or the composition, reply "Undo the changes to the face/outfit/composition and apply only the car change" rather than starting over. If it fails twice, start a new chat.
- Save each result as a new file (`SHOT_03_DOCK_PICKUP_v2.png` and so on). **Never overwrite the originals.** Put the new images in `wrong_delivery/pack/` and send them to me for the check below.

## Step 0: lock the car (do this first, once)
Shot 1 is the only picture that defines the car, and it shows only the front. Before fixing Shots 3 and 5 you need the side and rear designed once, so every later shot uses the same car. In a new chat attach `CAR_REFERENCE_from_SHOT_01.png` and `SHOT_01_CAR_CHASE.png`:

```
Create a vehicle reference sheet of the exact black sports car in the attached images. Do not redesign it. Show front three-quarter, side profile, and rear three-quarter on a plain dark-grey studio background, same wet-black paint finish. Keep: glossy black two-door performance coupe, low wide stance, angular blade-shaped cool-white LED headlights, black mesh grille with angular side intakes, vented hood, black multi-spoke wheels with red brake calipers, raised rear wing, dark interior with red stitching. No badges, no logos, no text, no license plate text. Photorealistic. 16:9.
```
Approve the side and rear views once, save the file as `CAR_SHEET_v1.png`, and attach it in every later car shot. The rear (taillights, exhaust) is the one part Shot 1 doesn't show, so you are choosing it here.

## Shot 3: dock pickup (car mismatch)
Attach: `SHOT_03_DOCK_PICKUP.png` (to edit), `CAR_SHEET_v1.png`, `SHOT_01_CAR_CHASE.png`, `CHAR_ALEX_CARTER.png`.
```
Edit the first image. Change ONLY the black sports car on the left so it is exactly the same car as in the car reference sheet and the Shot 1 image: angular blade-shaped cool-white LED headlight, black mesh grille with angular side intakes, vented hood, black multi-spoke wheels with red brake calipers, glossy wet-black paint. Remove the round twin projector headlights and the curved LED strip. Keep everything else identical: Alex's face, hair, charcoal tee, black leather jacket, jeans, boots and silver watch (matching the Alex character sheet), the brown taped box in his arms, the dock, containers, crane, ship, moon, wet ground, composition, framing, lighting and colour grade. No text, no logos, no weapons. 16:9.
```

## Shot 5: alley escape (car mismatch, pistol, pursuers)
Attach: `SHOT_05_ALLEY_ESCAPE.png` (to edit), `CAR_SHEET_v1.png`, `SHOT_01_CAR_CHASE.png`, `CHAR_ALEX_CARTER.png`.
```
Edit the first image with three changes only.
1) Alex's right hand: remove the pistol completely. His hand is empty and relaxed in a natural running position, five fingers, no object. Alex carries nothing.
2) The pursuers and police cars: move them much further back down the alley, far behind Alex, small dark figures roughly 60 to 80 metres away near the alley mouth, with the red and blue police lights glowing in the distance. None are close to Alex. Keep them as small distant silhouettes.
3) The black car on the right: make it exactly the car in the car reference sheet (rear three-quarter view): same body, wheels with red brake calipers, raised rear wing.
Keep everything else identical: Alex's face, hair, charcoal tee, black leather jacket, jeans, boots, silver watch, his running pose and direction, the wet alley, graffiti, steam, helicopter and searchlight, rain, colour grade and framing. No text, no logos. 16:9.
```

## Shot 6: dawn confrontation (lighting)
Attach: `SHOT_06_DAWN_CONFRONTATION.png` (to edit), both character sheets.
```
Edit the first image. Change ONLY the time-of-day lighting to a muted peach dawn: the sky above the ocean and city skyline becomes soft peach and pale gold near the horizon with a low rising sun and a light morning haze; remove all purple and magenta from the sky, the water and the city. The warm gold interior lamp and brass accents stay. Keep everything else identical: Mia's face, wavy hair, gold hoop earrings, burgundy satin blouse, cream blazer, black trousers, her pose in the chair; Alex's face, charcoal tee, black leather jacket and silver watch, his leaning pose; the dark marble desk, whisky decanter and glass, bookshelf, plant, windows, composition and framing. No text, no logos. 16:9.
```

## Acceptance check (send me the files and I will fill this in)
| Check | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|
| Face matches the character sheet (Alex / Mia) | | | | | | |
| Outfit matches (Alex: charcoal tee, black leather jacket, jeans, boots, silver watch / Mia: burgundy satin blouse, cream blazer, black trousers, gold hoops) | | | | | | |
| Hands: five fingers, natural | | | | | | |
| Car is the Shot 1 car (headlights, grille, wheels, rear wing) | ✔ | n/a (background) | | check interior | | n/a |
| No weapon in Alex's hands | ✔ | ✔ | ✔ | ✔ | | ✔ |
| Pursuers far behind | n/a | n/a | n/a | n/a | | n/a |
| Lighting as intended (night / night / night / night / night / **peach dawn**) | ✔ | ✔ | ✔ | ✔ | ✔ | |
| No readable text, logos or brand marks | | | | | | |
| 16:9, at least 1672×941 | ✔ | ✔ | ✔ | ✔ | | |
| Props: envelope (S2), brown taped box (S3), dark case with blue device (S4) | n/a | ✔ | ✔ | ✔ | n/a | n/a |

The ticks are what I could see in the originals; the blanks are what the new images must prove.
Shot 2: the car at the left of Alex is only background, so its exact shape does not matter unless it is in the video clip's moving area.
