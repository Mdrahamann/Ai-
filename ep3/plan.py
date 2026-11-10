"""Episode 3 single source of truth: every shot, line, cue and prompt lives here.

python3 plan.py  -> checks the timeline (continuous 0:00-6:00, dialogue fits at a gentle pace)
                    and writes production_package.md and shots.csv next to this file.
"""
import csv, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WPS, BREATH = 2.0, 0.5
RECURRING = "The truth feels lighter"
QUESTION = "What could Milo do?"

MILO = ("Milo, a small round fluffy yellow duckling with a little head tuft, an orange beak, pink cheeks, "
        "big glossy black eyes, tiny wings, short orange legs and shiny blue rain boots")
PIP = ("Pip, a small lavender bunny with long upright ears with pale pink insides, a cream muzzle and pale belly, "
       "a round white tail, big dark glossy eyes and a soft sage-green knitted scarf")
BUMBLE = ("Mr. Bumble, a big round friendly grown-up with a smooth yellow head, bushy brown eyebrows, big blue eyes, "
          "a round button nose, a wide toothy smile, a yellow shirt, gray trousers with light-blue suspenders and gray shoes")
STYLE = ("Soft rounded 3D preschool cartoon style, warm friendly colors, gentle soft daylight, clear readable faces, "
         "simple uncluttered background, no text, no logos")
SETS = {
    "kitchen": ("Mr. Bumble's cozy kitchen: soft sky-blue walls, a big window with a white sill and a cooling tray of star cookies, "
                "a wooden counter with a mixing bowl and a flour tin, a round white oven with a little window, "
                "a small round wooden table with three chairs, warm afternoon light"),
}
WM = {  # the tray of star cookies, by state
    "twelve": "a baking tray of twelve yellow-iced star cookies in three neat rows",
    "eleven": "a baking tray of yellow-iced star cookies in three rows with one empty spot and a few crumbs",
    "full": "a baking tray of twelve yellow-iced star cookies, one of them a little lopsided",
    "none": "",
}
ACTS = {"S01": "HOOK (0:00–0:15)", "S05": "WHY IT MATTERS (0:15–1:15)", "S14": "THE PROBLEM GETS BIGGER (1:15–2:45)",
        "S27": "THE TURNING POINT (2:45–4:15)", "S40": "THE PAYOFF (4:15–5:40)", "S52": "CLOSING (5:40–6:00)"}
DELIVERY = {("S15", "Milo"): " (too fast)", ("S21", "Milo"): " (whispering to himself)", ("S28", "Mr. Bumble"): " (gently)",
            ("S34", "Milo"): " (small voice)", ("S39", "Milo"): " (amazed)"}

SHOTS = [
 # ---------------- HOOK
 dict(id="S01", dur=5, kind="GEN", who="", set="kitchen", wm="twelve",
      action="Close-up of the cooling tray of twelve star cookies on the windowsill. A small yellow wing sneaks in from the side and takes one cookie.",
      framing="close-up on the tray", camera="static", lines=[], sound="Music: sneaky tiptoe pizzicato. SFX: tiny 'clink' as the cookie lifts."),
 dict(id="S02", dur=4, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo crouches behind the counter munching the cookie, cheeks round, crumbs on his beak, eyes wide.",
      framing="medium close-up on Milo peeking over the counter edge", camera="static", lines=[], sound="SFX: crunch, crunch, crunch."),
 dict(id="S03", dur=3, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble bustles in through the kitchen door with a big smile, clapping his hands.",
      framing="medium-wide shot of the doorway", camera="static", lines=[("Mr. Bumble", "Cookie time, friends!")], sound="SFX: door swing, happy footsteps. Music stops."),
 dict(id="S04", dur=3, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo gulps the last bite down in one big swallow, his eyes popping wide.",
      framing="close-up on Milo", camera="quick small push in", lines=[], sound="SFX: big cartoon GULP.", caption="UH-OH! (pill, top, 2 s)"),
 # ---------------- WHY IT MATTERS
 dict(id="S05", dur=7, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Wide shot of the kitchen: Mr. Bumble by the window, Pip at the table with an icing bag, Milo standing very still by the counter.",
      framing="wide three-shot", camera="slow push in", lines=[("Narrator", "Mr. Bumble baked star cookies for the garden party.")], sound="Music: warm kitchen theme."),
 dict(id="S06", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble holds up a little list of neighbors, counting on his fingers and smiling proudly.",
      framing="medium shot on Mr. Bumble", camera="static", lines=[("Mr. Bumble", "Twelve neighbors, twelve cookies. One for everyone!")], sound=""),
 dict(id="S07", dur=7, kind="GEN", who="P", set="kitchen", wm="eleven",
      action="Pip proudly holds up the yellow icing bag; there is a dab of yellow icing on the tip of her nose.",
      framing="medium shot on Pip at the table", camera="static", lines=[("Pip", "And we put on the sparkly icing!")], sound="SFX: little sparkle."),
 dict(id="S08", dur=8, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Mr. Bumble opens the flour tin and a big puff of flour covers his whole face white; he blinks twice. Pip and Milo laugh.",
      framing="medium three-shot", camera="static", lines=[("Mr. Bumble", "Oops! Now I'm a snowman!")], sound="SFX: flour POOF, blink-blink, everyone laughs. Music: comic sting."),
 dict(id="S09", dur=6, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo is laughing, then stops; he notices crumbs on his wings and quickly hides his wings behind his back.",
      framing="medium close-up on Milo", camera="static", lines=[], sound="Music: stops on a single plucked note."),
 dict(id="S10", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble, face still a little floury, carries the tray to the table.",
      framing="medium shot", camera="side tracking", lines=[("Mr. Bumble", "Let's count them, so nobody gets left out.")], sound="SFX: footsteps."),
 dict(id="S11", dur=7, kind="GEN", who="PB", set="kitchen", wm="eleven",
      action="Pip and Mr. Bumble count the cookies together, touching each one; Milo watches from the side.",
      framing="medium two-shot over the table", camera="slow pan along the tray", lines=[("Pip", "One, two, three, four, five, six...")], sound="SFX: soft 'tick' on each count."),
 dict(id="S12", dur=6, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble keeps counting, slowing down at the end of the last row.",
      framing="medium close-up on Mr. Bumble and the tray", camera="static", lines=[("Mr. Bumble", "Seven, eight, nine, ten, eleven...")], sound="SFX: ticks continue."),
 dict(id="S13", dur=5, kind="HOLD", who="", set="kitchen", wm="eleven",
      action="Close-up: the empty spot on the tray, with a few crumbs.",
      framing="close-up on the empty spot", camera="slow push in", lines=[("Mr. Bumble", "Eleven? That's funny.")], sound="Music: curious two-note sting."),
 # ---------------- PROBLEM GETS BIGGER
 dict(id="S14", dur=7, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Mr. Bumble scratches his head and looks around the kitchen; Pip looks up; Milo stands very straight.",
      framing="wide three-shot", camera="static", lines=[("Mr. Bumble", "Did somebody take a cookie?")], sound="Music: quiet, uneasy."),
 dict(id="S15", dur=6, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo freezes, then shakes his head very fast.",
      framing="close-up on Milo", camera="static", lines=[("Milo", "Not me!")], sound="SFX: quick head-shake 'brrrp'."),
 dict(id="S16", dur=7, kind="GEN", who="PB", set="kitchen", wm="eleven",
      action="Mr. Bumble notices the yellow dab on Pip's nose and looks at her, puzzled but kind.",
      framing="two-shot", camera="slow push in", lines=[("Mr. Bumble", "Pip, you have yellow on your nose...")], sound=""),
 dict(id="S17", dur=7, kind="GEN", who="P", set="kitchen", wm="eleven",
      action="Pip quickly wipes her nose, ears drooping, shaking her head.",
      framing="medium close-up on Pip", camera="static", lines=[("Pip", "That's icing! I didn't eat one.")], sound="SFX: small sniff."),
 dict(id="S18", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble looks at his neighbor list with a soft, sad face.",
      framing="medium shot", camera="static", lines=[("Mr. Bumble", "Hmm. Then one neighbor won't get a cookie.")], sound="Music: low, slow."),
 dict(id="S19", dur=6, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo holds his tummy; his whole body sinks lower and his tuft droops.",
      framing="medium close-up on Milo", camera="slow push in", lines=[("Narrator", "Milo's tummy felt heavy and wiggly.")], sound="SFX: low 'womp'."),
 dict(id="S20", dur=8, kind="STILL", who="MP", set="kitchen", wm="eleven",
      action="Quiet moment: Pip sits alone at the table with droopy ears; Milo watches her from behind the counter.",
      framing="wide shot", camera="slow push in over a still image", lines=[], sound="No music. Only the kitchen clock ticking."),
 dict(id="S21", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo, half hidden behind the counter, whispers to himself and twists his wings together.",
      framing="medium close-up on Milo", camera="static", lines=[("Milo", "If I tell, they might be mad.")], sound="Clock ticking."),
 dict(id="S22", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble tips the flour tin upside down; only a tiny puff comes out.",
      framing="medium shot", camera="static", lines=[("Mr. Bumble", "I'd bake one more, but my flour is all gone.")], sound="SFX: hollow tin tap, tiny puff."),
 dict(id="S23", dur=7, kind="GEN", who="P", set="kitchen", wm="eleven",
      action="Pip looks at the empty spot on the tray, ears low.",
      framing="medium close-up on Pip", camera="static", lines=[("Pip", "Someone will be left out.")], sound=""),
 dict(id="S24", dur=6, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Close-up: Milo's eyes go shiny; he squeezes his wings to his tummy.",
      framing="close-up on Milo", camera="very slow push in", lines=[("Narrator", "That heavy feeling has a name. It's guilt.")],
      sound="Music: soft single piano notes.", caption="GUILT (pill, top, 2 s)"),
 dict(id="S25", dur=8, kind="GEN", who="MB", set="kitchen", wm="eleven",
      action="Mr. Bumble lowers himself onto a little chair next to Milo, so their eyes are closer.",
      framing="two-shot", camera="static", lines=[("Mr. Bumble", "Milo, you look like a cloud is sitting on you.")], sound="SFX: little chair creak."),
 dict(id="S26", dur=7, kind="GEN", who="MB", set="kitchen", wm="eleven",
      action="Mr. Bumble smiles a small, remembering smile and pats his own tummy.",
      framing="two-shot", camera="slow push in", lines=[("Mr. Bumble", "Once, I broke my mom's teapot and hid it.")], sound="Music: warm, gentle."),
 # ---------------- TURNING POINT
 dict(id="S27", dur=8, kind="GEN", who="MB", set="kitchen", wm="eleven",
      action="Mr. Bumble shows with his hands how heavy it felt, then lifts them up lightly.",
      framing="two-shot", camera="static", lines=[("Mr. Bumble", "My tummy felt heavy for days. Then I told her.")], sound=""),
 dict(id="S28", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="Mr. Bumble leans in with a warm smile.",
      framing="medium close-up on Mr. Bumble", camera="slow push in", lines=[("Mr. Bumble", "And you know what? The truth feels lighter.")],
      sound="Music: the 'lighter' motif (three rising chimes), first time."),
 dict(id="S29", dur=6, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo looks down at the cookie crumbs still on his wings.",
      framing="close-up on Milo's face and wings", camera="static, hold", lines=[], sound="Silence."),
 dict(id="S30", dur=6, kind="STILL", who="MPB", set="kitchen", wm="eleven",
      action="All three in the kitchen; Milo between the counter and the table, thinking.",
      framing="wide three-shot", camera="slow push in over a still image", lines=[("Narrator", "What could Milo do?")], sound="Music: soft tick-tock bed.", note="Viewer question (the only one)."),
 dict(id="S31", dur=8, kind="HOLD", who="M", set="kitchen", wm="eleven",
      action="Milo thinks; a small thought bubble with three dots appears above his head.",
      framing="medium close-up on Milo", camera="static, hold", lines=[], pause=4.0, sound="Music: soft tick-tock bed. [PAUSE 4 s for viewers to answer]", note="Thought-dots icon added in edit."),
 dict(id="S32", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo takes a big breath, stands up tall, and walks out into the middle of the kitchen.",
      framing="medium-wide shot", camera="static", lines=[], sound="SFX: breath in, little boot steps. Music: soft drum build."),
 dict(id="S33", dur=7, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Milo looks up at Mr. Bumble and Pip; they both turn to listen.",
      framing="three-shot", camera="static", lines=[("Milo", "Mr. Bumble? Pip? I have to tell you something.")], sound=""),
 dict(id="S34", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo brings his wings out from behind his back, showing the crumbs.",
      framing="medium close-up on Milo", camera="slow push in", lines=[("Milo", "I ate the cookie. It was me.")], sound="Music: holds one soft note.",
      caption="TELLING THE TRUTH (pill, top, 3 s)"),
 dict(id="S35", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo looks down at his boots, then back up.",
      framing="medium close-up on Milo", camera="static", lines=[("Milo", "And I said not me. That wasn't true.")], sound=""),
 dict(id="S36", dur=7, kind="GEN", who="MP", set="kitchen", wm="eleven",
      action="Milo turns to Pip and speaks to her directly.",
      framing="two-shot", camera="static", lines=[("Milo", "I'm sorry, Pip. You got blamed because of me.")], sound=""),
 dict(id="S37", dur=6, kind="GEN", who="P", set="kitchen", wm="eleven",
      action="Pip's ears slowly come back up and she gives Milo a small smile.",
      framing="medium close-up on Pip", camera="static", lines=[("Pip", "Thank you for telling.")], sound="SFX: soft ear 'boing'."),
 dict(id="S38", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo's body rises up tall again; he pats his tummy, surprised.",
      framing="medium shot on Milo", camera="static", lines=[("Milo", "Hey... my tummy doesn't feel heavy anymore!")], sound="SFX: light 'floaty' whoosh up."),
 dict(id="S39", dur=7, kind="GEN", who="M", set="kitchen", wm="eleven",
      action="Milo bounces on his boots with a big smile.",
      framing="medium shot on Milo", camera="static", lines=[("Milo", "The truth feels lighter!")], sound="Music: the 'lighter' motif chimes, second time."),
 # ---------------- PAYOFF
 dict(id="S40", dur=7, kind="GEN", who="MB", set="kitchen", wm="eleven",
      action="Mr. Bumble kneels down and puts a big gentle hand on Milo's shoulder.",
      framing="two-shot", camera="static", lines=[("Mr. Bumble", "Thank you, Milo. That was brave.")], sound="Music: warm theme."),
 dict(id="S41", dur=7, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Mr. Bumble stands and looks at the empty spot on the tray, hand on chin.",
      framing="three-shot", camera="static", lines=[("Mr. Bumble", "Now, how do we fix the missing cookie?")], sound=""),
 dict(id="S42", dur=7, kind="GEN", who="P", set="kitchen", wm="eleven",
      action="Pip's ears shoot up with an idea and she hops toward the door.",
      framing="medium shot on Pip", camera="static", lines=[("Pip", "My house has flour! I'll get it!")], sound="SFX: idea 'ding', hop."),
 dict(id="S43", dur=7, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Pip hops back in with a little bag of flour; Milo and Mr. Bumble cheer.",
      framing="wide three-shot", camera="static", lines=[], sound="SFX: door, hops, cheer. Music: happy baking theme starts."),
 dict(id="S44", dur=8, kind="GEN", who="MPB", set="kitchen", wm="eleven",
      action="Baking together: Milo stirs the bowl slowly and carefully, Mr. Bumble rolls the dough, Pip cuts out a star; Milo's star comes out a little lopsided.",
      framing="medium three-shot at the counter", camera="slow pan", lines=[], sound="Music: happy baking theme. SFX: stir, roll, cut."),
 dict(id="S45", dur=7, kind="GEN", who="B", set="kitchen", wm="eleven",
      action="The oven goes ding; Mr. Bumble opens it and pulls out one lopsided golden star cookie.",
      framing="medium shot at the oven", camera="static", lines=[("Mr. Bumble", "Ta-da! A very special star.")], sound="SFX: oven DING, door open, sparkle."),
 dict(id="S46", dur=7, kind="GEN", who="MP", set="kitchen", wm="eleven",
      action="Milo ices the new cookie and gets a dab of yellow icing on his beak; Pip giggles and points.",
      framing="two-shot at the table", camera="static", lines=[("Pip", "Now you have icing on your nose!")], sound="SFX: giggles."),
 dict(id="S47", dur=7, kind="GEN", who="MPB", set="kitchen", wm="full",
      action="Milo places the lopsided star in the empty spot; all three count the last ones together.",
      framing="three-shot over the tray", camera="slow push in", lines=[("Mr. Bumble", "Ten, eleven..."), ("Milo", "Twelve!")], sound="SFX: ticks, then a big happy chime on 'Twelve!'"),
 dict(id="S48", dur=7, kind="HOLD", who="", set="kitchen", wm="full",
      action="Close-up of the full tray of twelve star cookies, the lopsided one sparkling.",
      framing="close-up on the tray", camera="slow push in", lines=[], sound="SFX: sparkle. Music: warm swell."),
 dict(id="S49", dur=7, kind="GEN", who="B", set="kitchen", wm="full",
      action="Mr. Bumble lifts the tray proudly.",
      framing="medium shot", camera="static", lines=[("Mr. Bumble", "One for every neighbor. Nobody left out.")], sound=""),
 dict(id="S50", dur=7, kind="GEN", who="MP", set="kitchen", wm="full",
      action="Milo hugs Pip; she hugs him back.",
      framing="two-shot", camera="static", lines=[("Milo", "Thanks for being my friend, Pip.")], sound="SFX: soft hug."),
 dict(id="S51", dur=7, kind="GEN", who="MPB", set="kitchen", wm="full",
      action="Mr. Bumble carries the tray toward the door to the garden party; Milo and Pip follow, hopping.",
      framing="wide shot", camera="side tracking", lines=[], sound="Music: theme. SFX: footsteps, hops."),
 # ---------------- CLOSING
 dict(id="S52", dur=7, kind="GEN", who="MPB", set="kitchen", wm="full",
      action="At the door Mr. Bumble sneezes; a puff of leftover flour covers all three of them white, and they laugh.",
      framing="three-shot", camera="static", lines=[("Mr. Bumble", "Ah... ah... CHOO!")], sound="SFX: big sneeze, flour POOF, laughter."),
 dict(id="S53", dur=7, kind="GEN", who="M", set="kitchen", wm="full",
      action="Milo, covered in flour, smiles at the camera.",
      framing="medium close-up on Milo", camera="slow push in", lines=[("Milo", "When I make a mistake, I'll tell the truth.")], sound="Music: theme outro."),
 dict(id="S54", dur=6, kind="STILL", who="MPB", set="kitchen", wm="full",
      action="End card: all three wave goodbye in the kitchen doorway, the cookie tray in Mr. Bumble's hands.",
      framing="wide shot", camera="slow pull back over a still image", lines=[], sound="Music: theme outro, fade out over the last 3 s.",
      caption="THE TRUTH FEELS LIGHTER (pill, center, last 5 s)", note="Leave room for YouTube end-screen elements."),
]

def mmss(s): return f"{s // 60}:{s % 60:02d}"

def words(t): return len(re.findall(r"[A-Za-z']+", t))

def need(sh):
    return sum(words(t) / WPS + BREATH for _, t in sh["lines"]) + sh.get("pause", 0)

def who_line(w):
    names = {"M": MILO, "P": PIP, "B": BUMBLE}
    parts = [names[c] for c in w]
    if not parts: return ""
    return (", and ".join([", ".join(parts[:-1]), parts[-1]]) if len(parts) > 1 else parts[0]) + "."

def gen_dur(d):
    return (d, None) if d >= 5 else (5, d)

def prompt(sh):
    if sh["kind"] == "REUSE":
        return None
    who = who_line(sh["who"]) or "No characters."
    setting = SETS[sh["set"]] + (f"; {WM[sh['wm']]}" if sh.get("wm") else "")
    g, trim = gen_dur(sh["dur"])
    speech = "Characters talk with gentle mouth movement." if any(w in ("Milo", "Pip", "Mr. Bumble") for w, _ in sh["lines"]) else "No dialogue, no lip-sync."
    still = sh["kind"] == "STILL"
    if still:
        return (f"{who} Setting: {setting}. Moment: {sh['action']} Framing: {sh['framing']}. "
                f"16:9, 1920x1080 still image. {STYLE}.")
    return (f"{who} Setting: {setting}. Action: {sh['action']} Framing: {sh['framing']}. Camera: {sh['camera']}. "
            f"Duration: {g} seconds, 16:9. {STYLE}. {speech}")

def check():
    t = 0
    for sh in SHOTS:
        sh["start"] = t; t += sh["dur"]; sh["end"] = t
        n = need(sh)
        assert n <= sh["dur"], f"{sh['id']} needs {n:.1f}s > {sh['dur']}s"
        assert 3 <= sh["dur"] <= 8, sh["id"]
    assert t == 360, t
    ids = [s["id"] for s in SHOTS]; assert ids == [f"S{i:02d}" for i in range(1, len(SHOTS) + 1)]
    recurring = [s["id"] for s in SHOTS for _, l in s["lines"] if RECURRING in l]
    assert len(recurring) == 2, recurring
    q = [s["id"] for s in SHOTS for _, l in s["lines"] if QUESTION in l]
    assert len(q) == 1
    return recurring, q

def main():
    recurring, q = check()
    total_words = sum(words(t) for s in SHOTS for _, t in s["lines"])
    tight = max(SHOTS, key=lambda s: need(s) / s["dur"])
    with open(os.path.join(HERE, "shots.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shot", "start", "end", "dur", "kind", "action", "dialogue", "sound", "caption"])
        for s in SHOTS:
            w.writerow([s["id"], mmss(s["start"]), mmss(s["end"]), s["dur"], s["kind"], s["action"],
                        " ".join(f'{a}: "{b}"' for a, b in s["lines"]) + (f" [PAUSE {s['pause']:.0f} s]" if s.get("pause") else ""),
                        s["sound"], s.get("caption", "")])
    md = open(os.path.join(HERE, "package_head.md")).read()
    out = [md]
    # ---- script
    out.append("\n## 2. Script\n\nAction lines are in *italics*. **[PAUSE]** = silence for viewers. **[SILENT]** = no dialogue; the picture carries it.\n")
    acts = ACTS
    for s in SHOTS:
        if s["id"] in acts: out.append(f"\n### {acts[s['id']]}\n")
        out.append(f"\n**{mmss(s['start'])} · {s['id']}** *{s['action']}*")
        if not s["lines"] and not s.get("pause"):
            out.append("  \n[SILENT]")
        for who, line in s["lines"]:
            delivery = ""
            delivery = DELIVERY.get((s["id"], who), "")
            out.append(f"  \n**{who.upper()}**{delivery}: {line}")
        if s.get("pause"): out.append(f"  \n**[PAUSE {s['pause']:.0f} s: viewers answer]**")
        if s.get("caption"): out.append(f"  \n> Caption: {s['caption']}")
    # ---- timeline
    out.append("\n\n## 3. Editing timeline\n\nPace check: 2 words per second plus 0.5 s per line (plus any viewer pause). **Fit** = seconds needed / seconds available.\n")
    out.append("| Shot | Start | End | Dur | Type | Visual action | Dialogue | Music / sound | Caption | Fit |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for s in SHOTS:
        dl = " ".join(f'{a}: "{b}"' for a, b in s["lines"]) or "(silent)"
        if s.get("pause"): dl += f" [PAUSE {s['pause']:.0f} s]"
        out.append(f"| {s['id']} | {mmss(s['start'])} | {mmss(s['end'])} | {s['dur']} s | {s['kind']} | {s['action']} | {dl} | {s['sound'] or '—'} | {s.get('caption', '—')} | {need(s):.1f}/{s['dur']} |")
    out.append(f"| **Total** | 0:00 | 6:00 | **360 s** | | | | | | |")
    out.append(f"\n**Checks (run `python3 plan.py`):** {len(SHOTS)} shots, each starting where the last ends, 0:00 → 6:00 with no gaps. "
               f"Every spoken shot fits at the gentle pace ({total_words} spoken words; tightest is {tight['id']} at {need(tight) / tight['dur']:.0%} of its time). "
               f"\"{RECURRING}\" is spoken exactly twice ({recurring[0]}, {recurring[1]}). "
               f"The viewer question is asked once ({q[0]}) with a 4 s pause for viewers to answer.")
    # ---- prompts
    out.append("\n\n## 4. AI video prompts\n")
    out.append(open(os.path.join(HERE, "prompts_head.md")).read())
    for s in SHOTS:
        g, trim = gen_dur(s["dur"])
        tag = {"GEN": "generate clip", "HOLD": "generate clip, then HOLD on the reaction", "STILL": "STILL image + slow move in the edit", "REUSE": "REUSE"}[s["kind"]]
        extra = f"; generate {g} s, trim to {trim} s" if trim else ""
        out.append(f"\n**{s['id']} ({mmss(s['start'])}–{mmss(s['end'])}, {s['dur']} s) · {tag}{extra}**")
        if s.get("note"): out.append(f"  \n_{s['note']}_")
        p = prompt(s)
        if p: out.append(f"\n```\n{p}\n```")
    out.append(open(os.path.join(HERE, "package_tail.md")).read())
    open(os.path.join(HERE, "production_package.md"), "w").write("\n".join(out))
    print(f"OK: {len(SHOTS)} shots, 360 s, {total_words} words, tightest {tight['id']} {need(tight):.1f}/{tight['dur']}")

if __name__ == "__main__":
    main()
