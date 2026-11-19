"""The Wrong Delivery, Episode 1 (8:00): single source for the screenplay, shot list and animation plan.

  python3 plan.py   -> checks the timeline (continuous, exactly 480 s, every line fits a gentle pace, story rules hold)
                       and writes episode1_shot_list.csv, EPISODE1_SCREENPLAY.md and ANIMATION_PLAN.md next to this file.

Story rules enforced by the check: Alex is never armed; the three props appear in order (flat dark envelope -> brown taped box ->
hard dark case with a blue glowing device); the pilot's six lines are all present; the dawn scene is a muted peach dawn.
Original fictional city (Caldera Bay). No real brands, no GTA branding.
"""
import csv, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
WPS, BREATH = 2.0, 0.5   # same gentle pace as the pilot: 2 words per second plus 0.5 s per line

ALEX, MIA, FOREMAN = "ALEX", "MIA", "FOREMAN"
# kind: CLIP = new AI motion clip needed | TITLE = graphic card (no AI clip)
# status: NEW | PROTOTYPE = a prototype clip exists but must be replaced (wrong car) | STORYBOARD = an original keyframe exists
# diff (animation risk): L low (environment, slow move, insert) | M medium (people talking/walking) | H high (car motion, running, action)
SCENES = [
 ("1", "COLD OPEN: THE CHASE", "EXT. CALDERA BAY WATERFRONT BOULEVARD, NIGHT, RAIN",
  "A black coupe tears along a rain-slick waterfront boulevard with police lights behind it. We do not yet know why."),
 ("2", "THREE HOURS EARLIER", "INT. ALEX'S LOCK-UP GARAGE / EXT. STREET, NIGHT, RAIN",
  "Alex Carter, a courier who is behind on everything, is offered one night's work by a stranger who knows his name."),
 ("3", "THE HANDOFF", "EXT. THE MERIDIAN CLUB, NIGHT, RAIN",
  "Mia Reyes gives Alex a flat dark envelope: instructions only, not the package."),
 ("4", "THE DRIVE", "EXT./INT. CITY STREETS AND TUNNEL, NIGHT",
  "A sedan follows him. He shakes it. He should have taken the hint."),
 ("5", "PIER NINETEEN", "EXT. PIER 19 CONTAINER YARD, NIGHT",
  "A foreman hands over a brown taped box and wants Alex gone. Someone else arrives looking for it."),
 ("6", "THE CASE", "INT. ALEX'S CAR, NIGHT, RAIN",
  "Alex opens the box. Inside is a hard dark case, and inside that, a blue glowing device. Mia calls. It is too late."),
 ("7", "THE RUN", "EXT. CALDERA BAY STREETS AND SERVICE ALLEY, NIGHT",
  "Police and private security close in. Alex hides the car, runs the pursuers away, doubles back, and escapes. He is unarmed."),
 ("8", "DAWN", "INT. MIA'S PENTHOUSE OFFICE, DAWN",
  "Muted peach dawn over the bay. Alex brings the case back and demands the truth."),
 ("9", "TAG", "INT. MIA'S OFFICE / EXT. STREET BELOW, DAWN",
  "The device wakes up. A black SUV waits below. The title lands."),
]
# (id, dur, kind, status, diff, in_frame, description, camera, lines[(who, text)], sound)
SHOTS = [
 ("1.01", 6, "CLIP", "PROTOTYPE", "H", "CAR", "The black coupe drives hard along the wet waterfront boulevard, water spraying from the tires, police lights far behind.", "low tracking shot alongside", [("ALEX (V.O.)", "Three hours ago, this was supposed to be a simple delivery.")], "rain, rising engine, tire spray, distant sirens"),
 ("1.02", 6, "CLIP", "NEW", "M", "ALEX", "Inside the car: Alex grips the wheel, eyes flicking to the mirror, jaw tight. Empty hands on the wheel, nothing else.", "close-up through the windscreen", [], "engine, rain on glass"),
 ("1.03", 6, "CLIP", "NEW", "M", "ALEX", "The mirror: two police cars and a helicopter searchlight sweeping the wet road behind him.", "close-up on the rear-view mirror", [], "sirens, helicopter rotor"),
 ("1.04", 8, "CLIP", "NEW", "H", "CAR", "The coupe slides through a wide turn and dives into an underpass, headlights stabbing through the rain.", "wide tracking shot, slight pan", [("ALEX", "Come on, come on, come on.")], "tire squeal, engine, echo in the underpass"),
 ("1.05", 6, "CLIP", "NEW", "L", "ALEX", "A cold blue glow pulses from the passenger footwell and washes over Alex's face. He glances down, then away.", "static close-up", [], "low electronic pulse"),
 ("1.06", 8, "CLIP", "NEW", "H", "CAR", "A police roadblock ahead. Alex cuts hard into a dark side street; the cruisers overshoot behind him.", "low front-quarter tracking shot", [], "sirens, tire squeal, impact of rain"),
 ("1.07", 8, "TITLE", "NEW", "L", "", "Hard cut to black. Title: THE WRONG DELIVERY. A low sting rises and stops dead.", "title card, no AI clip", [], "tension sting, silence"),
 ("2.01", 7, "CLIP", "NEW", "L", "", "Title super: THREE HOURS EARLIER. Caldera Bay at dusk in the rain, towers, harbour, neon switching on.", "slow aerial push in", [], "city ambience, rain"),
 ("2.02", 7, "CLIP", "NEW", "M", "ALEX,CAR", "A lock-up garage. Alex, sleeves rolled, works under the hood of the black coupe. A bare bulb swings. Unpaid notices are piled on the bench.", "slow side dolly", [], "wrench on metal, rain on tin roof"),
 ("2.03", 8, "CLIP", "NEW", "M", "ALEX", "His phone buzzes on the bench. He wipes his hands and answers.", "medium shot", [("MIA (PHONE)", "Still need the money?"), ("ALEX", "Who is this?")], "phone buzz, rain"),
 ("2.04", 6, "CLIP", "NEW", "L", "ALEX", "Close on Alex's face as he listens. We hear only the voice.", "slow push in", [("MIA (PHONE)", "Someone who needs a driver. Tonight.")], "room tone"),
 ("2.05", 7, "CLIP", "NEW", "L", "ALEX", "He looks at the stack of unpaid notices, then at the coupe. He decides.", "insert on the notices, then pan to Alex", [], "quiet, drip"),
 ("2.06", 7, "CLIP", "NEW", "M", "ALEX", "He shrugs on the weathered black leather jacket, straightens the silver watch on his wrist.", "medium close-up", [], "leather, zipper"),
 ("2.07", 8, "CLIP", "NEW", "M", "ALEX,CAR", "Alex gets into the coupe. The engine catches. He looks at himself in the mirror.", "over-the-shoulder", [("ALEX", "One job. That's all.")], "engine start"),
 ("2.08", 8, "CLIP", "NEW", "H", "CAR", "The car rolls out of the garage into the street, headlights sweeping across the wet road and the sign of the garage.", "wide shot from across the street", [("MIA (PHONE)", "Eleven o'clock. The Meridian Club. Don't be late.")], "engine, rain, phone voice"),
 ("3.01", 8, "CLIP", "NEW", "M", "CAR", "The Meridian Club: curved magenta canopy, warm-gold entrance, velvet ropes. The coupe pulls up on the wet asphalt.", "wide establishing shot, slow push in", [], "club bass through doors, rain"),
 ("3.02", 5, "CLIP", "NEW", "M", "ALEX", "Alex steps out and nods at the doorman.", "medium shot", [], "car door, rain"),
 ("3.03", 7, "CLIP", "NEW", "M", "MIA", "Mia Reyes comes out under a doorman's umbrella: burgundy satin blouse, cream blazer, gold hoops. She walks straight to him.", "low-angle tracking shot", [], "heels on wet stone, bass"),
 ("3.04", 8, "CLIP", "NEW", "M", "ALEX,MIA", "Two-shot over Alex's shoulder, the club glowing behind Mia.", "over-the-shoulder", [("MIA", "You're late."), ("ALEX", "You said eleven. It's ten fifty-eight.")], "rain, bass"),
 ("3.05", 8, "CLIP", "NEW", "M", "ALEX,MIA", "Mia does not smile. Alex rests an arm on the roof of the car.", "two-shot, slow push in", [("MIA", "Names don't matter tonight. Delivery does."), ("ALEX", "I drive. I don't deliver.")], "rain"),
 ("3.06", 7, "CLIP", "STORYBOARD", "M", "ALEX,MIA", "Mia holds out a flat dark envelope. Alex takes it.", "over-the-shoulder dolly in", [("MIA", "Pier Nineteen. Midnight. Do not open the package.")], "envelope rustle, rain"),
 ("3.07", 7, "CLIP", "NEW", "L", "ALEX", "Close on the envelope in Alex's hands. He tests its weight. Almost nothing.", "insert, shallow focus", [("ALEX", "What's in it?"), ("MIA", "Instructions. Nothing else.")], "paper"),
 ("3.08", 7, "CLIP", "NEW", "M", "MIA", "Mia steps closer and lowers her voice, rain on her hair.", "medium close-up", [("MIA", "If anyone asks, you never met me.")], "rain"),
 ("3.09", 6, "CLIP", "NEW", "M", "ALEX", "Alex pockets the envelope. Across the street a parked sedan, two men inside, watching. He sees them; Mia does not.", "slow pan from Alex to the sedan", [], "idle engine, rain"),
 ("3.10", 6, "CLIP", "NEW", "M", "MIA", "Mia walks back into the club. The doorman closes the velvet rope behind her.", "wide shot", [("ALEX", "Easy money.")], "bass swells, door shuts"),
 ("3.11", 7, "CLIP", "NEW", "M", "ALEX,CAR", "Alex is back in the car. In the rain-streaked side window we see the sedan's headlights come on.", "close on the window reflection", [], "engine, rain"),
 ("4.01", 8, "CLIP", "NEW", "H", "CAR", "The coupe glides through a tunnel of neon and rain. Behind it, a sedan keeps the same gap.", "tracking shot from behind", [], "tunnel echo, engine"),
 ("4.02", 8, "CLIP", "NEW", "M", "ALEX", "Alex checks the mirror and takes a sudden turn. In the mirror the sedan turns too.", "close-up on mirror, then Alex", [("ALEX", "Not a coincidence.")], "tire squeal"),
 ("4.03", 8, "CLIP", "NEW", "H", "CAR", "Alex runs a late amber light between two trucks. The sedan stops at red and falls out of frame.", "wide shot at the intersection", [], "horns, engine"),
 ("4.04", 8, "CLIP", "NEW", "L", "CAR", "The coupe slows at the gates of Pier 19: stacked containers, cranes, sodium lamps, a ship at anchor.", "slow push in through the gate", [], "harbour ambience, wind"),
 ("5.01", 8, "CLIP", "NEW", "M", "ALEX", "Pier 19 yard in light mist. Alex parks and steps out, the container stacks towering over him.", "wide shot, then medium", [], "wind, distant crane"),
 ("5.02", 7, "CLIP", "NEW", "M", "ALEX,FOREMAN", "A foreman at a container office door reads the envelope under a lamp.", "two-shot, side-on", [("FOREMAN", "Wrong night for visitors."), ("ALEX", "Pier Nineteen. Midnight.")], "wind, metal creak"),
 ("5.03", 8, "CLIP", "NEW", "M", "FOREMAN", "The foreman checks both ends of the yard and nods toward a stack.", "medium close-up", [("FOREMAN", "Forty-two B. Take the brown box. Nothing else.")], "wind"),
 ("5.04", 7, "CLIP", "NEW", "M", "ALEX", "Alex walks the narrow corridor between containers, cranes looming above.", "slow tracking shot from behind", [], "footsteps in puddles, creak"),
 ("5.05", 8, "CLIP", "NEW", "M", "ALEX", "A medium brown taped box on a pallet, a crane load swinging far above. Alex lifts it. Heavier than it looks.", "medium shot", [("ALEX", "It's heavy.")], "crane chain, creak"),
 ("5.06", 7, "CLIP", "STORYBOARD", "M", "ALEX,CAR", "Alex carries the box past his coupe and stops, turning toward distant footsteps.", "side dolly past the car", [("ALEX (V.O.)", "I should have walked away the moment I saw that box.")], "footsteps, harbour wind"),
 ("5.07", 8, "CLIP", "NEW", "M", "ALEX", "At the end of the corridor two silhouettes with flashlights search the stacks. Alex ducks behind a container.", "over-the-shoulder, low", [], "flashlight click, distant voices"),
 ("5.08", 7, "CLIP", "NEW", "M", "ALEX", "A flashlight beam crosses the wet metal inches from him. He holds his breath.", "extreme close-up", [], "heartbeat, rain"),
 ("5.09", 8, "CLIP", "NEW", "M", "ALEX,CAR", "He slips to the coupe and sets the box on the passenger seat. He closes the door softly.", "medium shot", [], "door latch, rain"),
 ("6.01", 7, "CLIP", "NEW", "M", "ALEX", "Inside the car, doors locked, rain drumming on the roof. Alex stares at the box.", "close-up through the side window", [("ALEX", "Do not open the package.")], "rain on roof"),
 ("6.02", 6, "CLIP", "NEW", "L", "ALEX", "He slits the tape with his car key and pulls open the flaps.", "insert on hands", [], "tape rip"),
 ("6.03", 8, "CLIP", "STORYBOARD", "L", "ALEX", "Inside the box, a hard dark case. A latch clicks. Blue light leaks from under the lid.", "slow push in", [("ALEX", "What the hell is this?")], "latch click, electronic pulse"),
 ("6.04", 8, "CLIP", "NEW", "L", "ALEX", "The lid rises. A blue glowing device pulses inside. Alex's face is lit blue.", "very slow push in", [], "rising low pulse"),
 ("6.05", 8, "CLIP", "NEW", "M", "ALEX", "His phone buzzes: MIA. He answers without taking his eyes off the glow.", "medium close-up", [("ALEX", "It's glowing, Mia."), ("MIA (PHONE)", "Close it. Close it now.")], "phone buzz, pulse"),
 ("6.06", 7, "CLIP", "NEW", "H", "ALEX,CAR", "In the mirror, three sets of headlights turn in at the pier gate. Alex slams the case shut.", "mirror close-up, then wide", [("MIA (PHONE)", "Drive. Don't stop. Don't call anyone.")], "case slam, engines, rain"),
 ("7.01", 7, "CLIP", "NEW", "H", "CAR", "The coupe launches, tires spinning on wet concrete. Container stacks blur past.", "low tracking shot", [], "engine roar, tire spray"),
 ("7.02", 6, "CLIP", "NEW", "H", "CAR", "Two black SUVs and a police cruiser pour out of side roads behind him, sirens rising.", "wide shot from above", [], "sirens, engines"),
 ("7.03", 8, "CLIP", "PROTOTYPE", "H", "CAR", "The chase down the waterfront. Alex weaves between cars, water exploding from the tires.", "low front-quarter tracking shot", [("ALEX (V.O.)", "By then, half the city was looking for me.")], "engine, rain, sirens"),
 ("7.04", 8, "CLIP", "NEW", "H", "ALEX,CAR", "Close on Alex weaving; sparks scrape under the car. The engine coughs.", "tight shot through the windscreen", [("ALEX", "Not now!")], "sparks, engine strain"),
 ("7.05", 7, "CLIP", "NEW", "H", "CAR", "Alex swings the coupe into a dead-end service alley, kills the lights, and rolls to a stop in the dark.", "high rear tracking shot", [], "tires on wet stone, engine off"),
 ("7.06", 8, "CLIP", "STORYBOARD", "H", "ALEX", "Alex gets out, empty-handed but for the case, and runs out the far end of the alley. Far behind at the mouth, flashlights and police lights; the pursuers are small and distant.", "low-angle tracking shot", [], "running footsteps, sirens, helicopter"),
 ("7.07", 8, "CLIP", "NEW", "H", "ALEX", "He doubles back along a parallel lane, steam rising, a helicopter searchlight sweeping the rooftops.", "tracking shot beside him", [], "footsteps, helicopter"),
 ("7.08", 8, "CLIP", "NEW", "M", "ALEX,CAR", "Alex reaches the dark coupe, throws himself in, turns the key. The helicopter light finds the alley.", "close-up", [("ALEX", "Start. Please start.")], "engine catches, rotor"),
 ("7.09", 6, "CLIP", "NEW", "H", "CAR", "The coupe bursts out of the alley under the searchlight, spray and red taillights, and is gone.", "wide shot, locked off", [], "engine roar, cut to silence"),
 ("8.01", 8, "CLIP", "NEW", "L", "", "Muted peach dawn over Caldera Bay: pale gold at the horizon, soft haze, a glass tower catching the first light.", "slow tilt up the tower", [], "gulls, distant traffic"),
 ("8.02", 7, "CLIP", "NEW", "M", "ALEX", "Alex rides the mirrored elevator, the case in his hand, jaw set, rain still on his jacket.", "medium shot", [], "elevator hum"),
 ("8.03", 8, "CLIP", "NEW", "M", "MIA", "The doors open. Mia sits behind a dark marble desk, calm, a decanter and one glass beside her.", "wide shot, slow dolly in", [("MIA", "You came back.")], "room tone"),
 ("8.04", 8, "CLIP", "NEW", "M", "ALEX,MIA", "Alex sets the case on the desk. Mia does not look at it.", "two-shot", [("ALEX", "You told me it was a package."), ("MIA", "It was.")], "case on marble"),
 ("8.05", 8, "CLIP", "NEW", "M", "ALEX", "Alex, tired and furious, leans on the desk.", "medium close-up", [("ALEX", "Men with guns chased me across the city. It glows, Mia.")], "room tone"),
 ("8.06", 8, "CLIP", "NEW", "M", "MIA", "Mia finally lifts her eyes to him, steady.", "close-up", [("MIA", "They weren't after you. They were after it.")], "quiet"),
 ("8.07", 9, "CLIP", "NEW", "M", "ALEX,MIA", "Alex stares at her. The peach light crosses the desk.", "two-shot, slow push in", [("ALEX", "Then why send me?"), ("MIA", "You were never meant to deliver it.")], "quiet, rising tone"),
 ("8.08", 8, "CLIP", "STORYBOARD", "M", "ALEX,MIA", "Alex leans over the desk. Mia slowly lifts her gaze to him.", "slow lateral dolly", [("ALEX", "Then what was I meant to do?"), ("MIA", "You were meant to disappear.")], "tension sting begins"),
 ("9.01", 8, "CLIP", "NEW", "L", "MIA", "Close on the glowing case on the desk. The pulse quickens. Mia glances at it.", "slow push in", [("MIA", "And now it knows your name.")], "pulse quickens"),
 ("9.02", 8, "CLIP", "NEW", "M", "ALEX", "Alex looks at his own blue-lit hands. Through the glass, far below, a black SUV pulls up in the street.", "over-the-shoulder to the window", [("ALEX (V.O.)", "That's when I understood the delivery was never the job.")], "pulse, street ambience"),
 ("9.03", 8, "TITLE", "NEW", "L", "", "Hard cut to black. End card: THE WRONG DELIVERY, EPISODE 2 SOON.", "title card, no AI clip", [], "sting, silence"),
]

def words(t): return len(re.findall(r"[A-Za-z']+", t))
def need(sh): return sum(words(t) / WPS + BREATH for _, t in sh[8])
def mmss(s): return f"{s // 60}:{s % 60:02d}"

def check():
    t = 0; rows = []
    for sh in SHOTS:
        rows.append((t, sh)); t += sh[1]
    assert t == 480, f"runtime is {t}, not 480"
    ids = [s[0] for s in SHOTS]; assert len(ids) == len(set(ids))
    for st, sh in rows: assert need(sh) <= sh[1], f"{sh[0]} needs {need(sh):.1f}s > {sh[1]}s"
    # scene lengths are contiguous and each scene exists
    assert [s[0].split(".")[0] for s in SHOTS] == sorted([s[0].split(".")[0] for s in SHOTS])
    text = " ".join(x for sh in SHOTS for _, x in sh[8]).lower()
    for line in ["three hours ago, this was supposed to be a simple delivery", "pier nineteen. midnight. do not open the package", "i should have walked away the moment i saw that box",
                 "what the hell is this", "by then, half the city was looking for me", "you were never meant to deliver it", "you were meant to disappear"]:
        assert line in text, f"pilot line missing: {line}"
    alltext = " ".join(sh[6] + " " + " ".join(x for _, x in sh[8]) for sh in SHOTS).lower()
    for bad in ["pistol", "gun in alex", "alex fires", "shoots"]: assert bad not in alltext.replace("men with guns chased", ""), bad
    assert "envelope" in alltext and "brown taped box" in alltext and "blue glowing device" in alltext
    return rows

ATTEMPTS = {"L": 1.5, "M": 2.0, "H": 3.0}   # planning assumption: expected generations per usable clip
RATES = {"Runway Gen-4 Turbo (about 5 credits per second, third-party figure)": 5.0,
         "Higgsfield Kling 3.0 standard (9 credits per 6 s clip, checked in this project)": 1.5,
         "Higgsfield Kling 3.0 pro (10.5 credits per 6 s clip, checked in this project)": 1.75}

def animation_plan(rows):
    clips = [(st, s) for st, s in rows if s[2] == "CLIP"]; scenes = {}
    for st, s in clips:
        n = s[0].split(".")[0]; d = scenes.setdefault(n, dict(c=0, sec=0, gen=0.0, gsec=0.0, H=0))
        d["c"] += 1; d["sec"] += s[1]; d["gen"] += ATTEMPTS[s[4]]; d["gsec"] += ATTEMPTS[s[4]] * s[1]; d["H"] += s[4] == "H"
    T = dict(c=sum(d["c"] for d in scenes.values()), sec=sum(d["sec"] for d in scenes.values()), gen=sum(d["gen"] for d in scenes.values()), gsec=sum(d["gsec"] for d in scenes.values()))
    sc = {s[0]: s for s in SCENES}; o = []
    o.append("# Episode 1: animation plan\n")
    o.append("_Generated by `plan.py` from the shot list. Nothing here has been purchased or run. Credit figures are planning estimates: only the Higgsfield rows were checked in this project; the Runway figure comes from third-party pages._\n")
    o.append("## What has to be made\n")
    o.append(f"- **{T['c']} AI motion clips** covering **{T['sec']} s** of the 480 s film, plus 2 title cards (16 s) that need no clip.")
    o.append("- Two of those clips exist as **prototype footage** (1.01 and 7.03). They show the wrong cars (a different supercar in each, one with a visible brand badge and a legible license plate), so they are placeholders to be **replaced**, not final.")
    o.append("- Five **original storyboard keyframes** exist (3.06, 5.06, 6.03, 7.06, 8.08). 3.06 and 6.03 are usable as start images. 5.06 (car design), 7.06 (pistol, close pursuers) and 8.08 (purple sunset) need the corrections already specified in `IMAGE_CORRECTION_CHECKLIST.md` first.")
    o.append("- Every other clip needs a **start image** (keyframe) made first. That is **about 58 new keyframes**, each checked against the character sheets and the car sheet before it is animated. This is the biggest job; the clips are the second biggest.\n")
    o.append("## Cost, in credits (not money)\n")
    o.append(f"Planning assumption: an average of {ATTEMPTS['L']} generations per low-risk clip, {ATTEMPTS['M']} per medium-risk clip and {ATTEMPTS['H']} per high-risk clip (car motion, running), because cars, hands and faces fail often. That is about **{T['gen']:.0f} generations and {T['gsec']:.0f} s of generated video** to get {T['sec']} s of usable footage.\n")
    o.append("| Tool and rate | Credits for the whole episode |\n|---|---|")
    for k, v in RATES.items(): o.append(f"| {k} | about {T['gsec'] * v:,.0f} |")
    o.append("\nWhat free tiers can do: Runway's free plan is reported as about 125 one-time credits, which is roughly 25 s of Gen-4 Turbo video or **about 2.5% of what this episode needs**, and it adds a watermark and 720p. So **the full 8-minute episode cannot be made on free credits.** You have not approved spending, and I won't spend anything. Your real options are below.\n")
    o.append("## Per scene\n")
    o.append("| Scene | Clips | Seconds | High-risk clips | Expected generations | Runway credits (est.) | Higgsfield Kling std credits (est.) |\n|---|---|---|---|---|---|---|")
    for n, d in scenes.items(): o.append(f"| {n}. {sc[n][1].title()} | {d['c']} | {d['sec']} | {d['H']} | {d['gen']:.0f} | {d['gsec'] * 5:,.0f} | {d['gsec'] * 1.5:,.0f} |")
    o.append(f"| **Total** | **{T['c']}** | **{T['sec']}** | | **{T['gen']:.0f}** | **{T['gsec'] * 5:,.0f}** | **{T['gsec'] * 1.5:,.0f}** |\n")
    o.append("## Order of work (each step is a gate; stop and review at every gate)\n")
    o.append("1. **Gate 0, done:** prototype rough cut of 33.5 s (14 s AI clips, 19.5 s labelled stills) with voices and sound.")
    o.append("2. **Gate 1, car and images:** you approve the car turnaround (Step 0 in the kit) and the corrected Shots 3, 5, 6. Nothing else should be generated before the car is locked, because the car appears in 21 shots.")
    o.append("3. **Gate 2, the one real test:** one 5 s Shot 1 clip from the original Shot 1 image. If a free tool cannot keep the car's shape and wheels believable, **we stop and rethink the tool**, not the plan.")
    o.append("4. **Gate 3, the 32 s pilot:** six clips (Shots 1 to 6 of the pilot) with the voices already made. This is also the proof for you: does it look like the AAA game-cinema target?")
    o.append("5. **Scene by scene, hardest first within each scene:** car shots (H) before talking shots (M) before inserts (L), so a failing car shot is found early. Generate, run `qc.py`, look at the contact sheet, keep or retake. Do not generate the next scene until the current one passes.")
    o.append("6. **Final assembly** with `timeline.py` (real clips only), the quality check on the finished file, and the licence and disclosure checks.\n")
    o.append("## Paths forward (you choose; none is started)\n")
    o.append("- **A. Pay for credits later, when you decide to.** Cheapest sensible route: Higgsfield Kling standard, roughly 1,500 credits for the whole episode by the estimate above. I'd confirm the real plan price with you first and run nothing without your yes.")
    o.append("- **B. Build it slowly on free allowances** from several tools, a few clips at a time. Every free clip is 720p and watermarked, so it only works as a **preview version**, never a clean release, and the allowances change often.")
    o.append("- **C. A shorter first episode.** Keep the 8-minute screenplay as the master, but release a 2 to 3 minute **cold open + dawn scene** first (scenes 1 and 8 plus the title and tag: about 26 clips). Smaller, finishable, and a real test of whether the channel gets an audience before the big spend.")
    o.append("- **D. Hybrid with storyboard stills.** Real motion only for the 15 high-risk action clips and the hero shots; the rest as clearly labelled stills with the voices. It would not be a fully animated film, and I would label it that way.\n")
    o.append("## Quality rules for every clip (unchanged)\n")
    o.append("Real motion only (the checker rejects a still with a camera move); the car must be the Shot 1 car; Alex and Mia match their sheets; Alex is unarmed; no readable text, brand marks or license plates; no watermark; native 1080p preferred and any upscale recorded. The checker handles the numbers; the faces, hands, car shape and wheels are checked by eye on the contact sheet.")
    open(os.path.join(HERE, "ANIMATION_PLAN.md"), "w").write("\n".join(o) + "\n")
    return T

def main():
    rows = check()
    csvp = os.path.join(HERE, "episode1_shot_list.csv")
    with open(csvp, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["shot", "scene", "start", "end", "dur_s", "type", "asset_status", "animation_risk", "in_frame", "visual", "camera", "dialogue", "sound"])
        for st, sh in rows:
            w.writerow([sh[0], sh[0].split(".")[0], mmss(st), mmss(st + sh[1]), sh[1], sh[2], sh[3], sh[4], sh[5], sh[6], sh[7], " / ".join(f'{a}: "{b}"' for a, b in sh[8]), sh[9]])
    # screenplay
    sc = {s[0]: s for s in SCENES}; out = []
    out.append("# THE WRONG DELIVERY: Episode 1 (8:00)\n")
    out.append("_An original fictional crime film set in Caldera Bay. Photorealistic open-world-game look. Not affiliated with any existing game. Alex is unarmed throughout._\n")
    out.append("**Logline.** A broke courier takes one night's work as a getaway driver. By dawn he learns the delivery was never the job.\n")
    out.append("**Cast.** ALEX CARTER (27, wary, capable; charcoal tee, weathered black leather jacket, dark jeans, boots, silver watch; unarmed). MIA REYES (29, controlled, mysterious; burgundy satin blouse, cream blazer, black trousers, gold hoops). FOREMAN (50s, tired, careful; new character, needs a reference sheet). Pursuers: a grey sedan crew, black SUVs and police (new, far away, faceless).\n")
    out.append("**Props, in order.** flat dark envelope (instructions only) -> medium brown taped box -> hard dark case -> blue glowing device. They are four different things on purpose.\n")
    out.append("**Car.** The black performance coupe from Shot 1 (permanent design: thin blade LED headlights, honeycomb grille, hood vents, rear wing, black wheels, red calipers).\n")
    out.append("**Pacing note.** Dialogue is written at a gentle 2 words per second so each line fits its shot in AI-generated clips of 5 to 9 seconds.\n")
    cur = None
    for st, sh in rows:
        n = sh[0].split(".")[0]
        if n != cur:
            cur = n; s = sc[n]
            out.append(f"\n---\n\n## SCENE {n}: {s[1]}  ({mmss(st)})\n\n**{s[2]}**\n\n_{s[3]}_\n")
        out.append(f"\n**[{sh[0]} · {mmss(st)} · {sh[1]} s]** {sh[6]}")
        for who, line in sh[8]:
            out.append(f"\n&nbsp;&nbsp;&nbsp;&nbsp;**{who}**: {line}")
        out.append("")
    out.append("\n---\n\n**END OF EPISODE 1**\n")
    open(os.path.join(HERE, "EPISODE1_SCREENPLAY.md"), "w").write("\n".join(out))
    # animation plan numbers
    clips = [s for s in SHOTS if s[2] == "CLIP"]; secs = sum(s[1] for s in clips)
    byrisk = {k: (len([s for s in clips if s[4] == k]), sum(s[1] for s in clips if s[4] == k)) for k in "LMH"}
    words_total = sum(words(x) for s in SHOTS for _, x in s[8]); lines_total = sum(len(s[8]) for s in SHOTS)
    meta_T = animation_plan(rows)
    meta = dict(shots=len(SHOTS), clips=len(clips), secs=secs, byrisk=byrisk, titles=len(SHOTS) - len(clips), prototype=[s[0] for s in SHOTS if s[3] == "PROTOTYPE"],
                storyboard=[s[0] for s in SHOTS if s[3] == "STORYBOARD"], words=words_total, lines=lines_total, tightest=max(SHOTS, key=lambda s: need(s) / s[1]))
    return meta

if __name__ == "__main__":
    m = main(); t = m["tightest"]
    print(f"OK: {m['shots']} shots = 480 s; {m['clips']} AI clips ({m['secs']} s) + {m['titles']} title cards; {m['lines']} lines, {m['words']} words; tightest {t[0]} {need(t):.1f}/{t[1]}")
    print("by risk (clips, seconds):", m["byrisk"]); print("prototype clips to replace:", m["prototype"]); print("storyboard stills available:", m["storyboard"])
