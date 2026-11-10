"""Episode 2 single source of truth: every shot, line, cue and prompt lives here.

python3 plan.py  -> checks the timeline (continuous 0:00-6:00, dialogue fits at a gentle pace)
                    and writes production_package.md and shots.csv next to this file.
"""
import csv, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WPS, BREATH = 2.0, 0.5   # gentle pace: 2 words per second + 0.5 s per line

MILO = ("Milo, a small round fluffy yellow duckling with a little head tuft, an orange beak, pink cheeks, "
        "big glossy black eyes, tiny wings, short orange legs and shiny blue rain boots")
PIP = ("Pip, a small lavender bunny with long upright ears with pale pink insides, a cream muzzle and pale belly, "
       "a round white tail, big dark glossy eyes and a soft sage-green knitted scarf")
STYLE = ("Simple flat 2D cartoon animation for preschoolers, soft rounded shapes, clean dark outlines, "
         "warm cozy colors, clear readable faces and expressions, simple uncluttered background, no text, no logos")
SETS = {
    "porch": ("Pip's sunny back porch in the late afternoon: warm wooden floorboards, a low white railing, a small "
              "round craft table, a cream-and-peach house wall with a round window, a clay flowerpot on the railing, "
              "tall grass swaying in the garden beyond, warm golden light"),
    "craft": ("a cozy craft corner inside Pip's house in the morning: a round wooden table with colored paper squares, "
              "a glue stick, round-tip kid scissors and a roll of tape, a small craft box with paper scraps "
              "including one rainbow-striped scrap, warm cream walls, a window with soft morning sun"),
}
WM = {
    "parts": "a half-built paper windmill on the table: a wooden stick and three square paper blades, red, yellow and green, with a blue blade still loose",
    "almost": "a small paper windmill on a wooden stick with three blades attached, red, yellow and green, and Milo holding the last blue blade",
    "torn": "a small paper windmill on a wooden stick with four square paper blades, red, yellow, green and blue; the blue blade has a rip along one edge",
    "worse": "a small paper windmill on a wooden stick with four paper blades, red, yellow, green and blue; the blue blade is torn halfway and hangs loose",
    "patched": "a small paper windmill on a wooden stick with four paper blades, red, yellow, green and blue; the blue blade is mended with a small rainbow-striped paper patch",
}

# kind: GEN (new clip) | HOLD (generate short, hold/extend the reaction) | STILL (one image + slow pan/push in edit)
#       REUSE (reuse an earlier clip) ; bg: shot whose background/plate can be reused
# fields: id, dur, kind, who, set, windmill, action, framing, camera, lines[(who,text)], pause, sound, caption, note
SHOTS = [
 # ---------------- 0:00-0:15 HOOK
 dict(id="S01", dur=5, kind="GEN", who="MP", set="porch", wm="almost",
      action="Milo stands on tiptoe on a little stool and presses the last blue blade onto the windmill while Pip holds the base of the stick steady with both paws. The grass behind them starts to bend in the wind.",
      framing="medium-wide two-shot, both characters and the windmill centered", camera="static",
      lines=[("Milo", "Last piece... got it!")], sound="Music: light, bouncy theme (low). SFX: wind starting to rise, paper rustle."),
 dict(id="S02", dur=4, kind="GEN", who="", set="porch", wm="torn",
      action="A strong gust hits the paper windmill; the blue blade bends back and rips along one edge with a little flutter of paper.",
      framing="close-up on the windmill blades", camera="static",
      lines=[], sound="SFX: big wind gust 'whoosh' (the WIND MOTIF), loud paper RRRIP. Music cuts out on the rip."),
 dict(id="S03", dur=3, kind="HOLD", who="M", set="porch", wm="torn",
      action="Milo's feathers puff up, his wings clench the torn blue blade, his brows pinch down and he shouts toward Pip.",
      framing="close-up on Milo's face and wings", camera="quick small push in",
      lines=[("Milo", "You let go!")], sound="SFX: short 'boing' sting on the shout.", caption="FRUSTRATED (orange pill, lower third, 2 s)"),
 dict(id="S04", dur=3, kind="HOLD", who="P", set="porch", wm="torn",
      action="Pip's ears slowly droop. Without a word she lifts her paws a little to show she is still holding the base of the windmill stick.",
      framing="close-up on Pip, her paws on the stick at the bottom of frame", camera="static, hold",
      lines=[], sound="Silence except a soft breeze. A single low piano note."),
 # ---------------- 0:15-1:15 WHY IT MATTERS
 dict(id="S05", dur=7, kind="GEN", who="MP", set="craft", wm="parts",
      action="Milo and Pip sit at the craft table surrounded by colored paper. Milo holds up a crayon drawing of a windmill; Pip leans in to look.",
      framing="wide two-shot across the table", camera="slow push in",
      lines=[("Narrator", "This morning, Milo and Pip had a big idea.")], sound="Transition: soft rewind 'whirr' and page-flip swoosh. Music: warm morning theme.",
      caption="THIS MORNING (location-tag pill, top center, 3 s)"),
 dict(id="S06", dur=7, kind="GEN", who="M", set="craft", wm="parts",
      action="Milo bounces on his chair, waving the windmill drawing excitedly.",
      framing="medium shot on Milo at the table", camera="static",
      lines=[("Milo", "Let's build a windmill! One that really spins!")], sound="SFX: chair squeak, paper flap."),
 dict(id="S07", dur=6, kind="GEN", who="MP", set="craft", wm="parts",
      action="Pip picks up the wooden stick and holds it upright with both paws, smiling; Milo grabs a red paper square.",
      framing="medium two-shot", camera="static",
      lines=[("Pip", "Okay! I'll hold, you build.")], sound="Music: playful building theme starts."),
 dict(id="S08", dur=8, kind="GEN", who="MP", set="craft", wm="parts",
      action="Building montage: Milo folds a red blade and pins it on, then a yellow one, then a green one, while Pip keeps the stick perfectly still.",
      framing="close-up on wings, paws and paper at the table", camera="slow pan left to right",
      lines=[], sound="SFX: paper folds, little 'tick' on each blade. Music: building theme."),
 dict(id="S09", dur=7, kind="GEN", who="MP", set="craft", wm="parts",
      action="Milo flaps one wing and finds the green blade glued to it; he flaps again and the blade flaps along with his wing. Pip covers her mouth, giggling.",
      framing="medium two-shot", camera="static",
      lines=[("Milo", "Um... Pip? I'm stuck.")], sound="SFX: sticky 'thwip', flap-flap, Pip giggles. Music: comic pizzicato."),
 dict(id="S10", dur=7, kind="GEN", who="MP", set="craft", wm="parts",
      action="Pip gently peels the paper off Milo's wing; a tiny paper scrap stays stuck on his head tuft like a little hat. Both burst out laughing.",
      framing="medium two-shot", camera="slow push in",
      lines=[("Pip", "Ta-da! Now you have a paper hat!")], sound="SFX: gentle peel, both laugh."),
 dict(id="S11", dur=8, kind="GEN", who="M", set="craft", wm="almost",
      action="Milo stands back with his chest puffed out, wings on hips, looking proudly at the windmill with three blades on; he holds the last blue blade.",
      framing="medium shot, low angle on Milo with the windmill beside him", camera="slow push in",
      lines=[("Milo", "Look, Pip. We made this. Together!")], sound="Music: warm, proud swell."),
 dict(id="S12", dur=5, kind="GEN", who="MP", set="porch", wm="almost",
      action="Milo and Pip carry the windmill out onto the porch together, Milo holding the last blue blade high.",
      framing="wide shot, the friends walking left to right", camera="side tracking",
      lines=[("Narrator", "Just one more blade to go.")], sound="SFX: door creak, footsteps on wood."),
 dict(id="S13", dur=5, kind="REUSE", who="", set="porch", wm="torn",
      action="Quick replay of the gust and the rip (reuse S02, slowed to 80%).",
      framing="close-up on the windmill blades", camera="static",
      lines=[("Narrator", "And then... the wind came.")], sound="SFX: WIND MOTIF gust again, quieter. RRRIP.", note="Reuse S02 at 80% speed; no new clip."),
 # ---------------- 1:15-2:45 THE PROBLEM GETS BIGGER
 dict(id="S14", dur=6, kind="GEN", who="MP", set="porch", wm="torn",
      action="Pip, still holding the stick, speaks softly and nods at her paws; Milo turns his back to her with his wings crossed.",
      framing="two-shot, Pip left, Milo right", camera="static",
      lines=[("Pip", "Milo, I didn't let go. See?")], sound="Music: quiet, uneasy low strings."),
 dict(id="S15", dur=6, kind="GEN", who="M", set="porch", wm="torn",
      action="Milo hunches over, squeezing the torn blue blade tight in his wings, stamping one blue boot.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "But it's broken! It's ruined!")], sound="SFX: boot stamp on wood, paper crinkle."),
 dict(id="S16", dur=7, kind="GEN", who="MP", set="porch", wm="torn",
      action="Pip reaches out a paw to help; Milo pulls the windmill toward himself and grabs the roll of tape from the table.",
      framing="two-shot", camera="static",
      lines=[("Pip", "We can fix it. Slowly..."), ("Milo", "No! I'll fix it! Fast!")], sound="SFX: tape roll grabbed."),
 dict(id="S17", dur=7, kind="GEN", who="M", set="porch", wm="torn",
      action="Milo rips off tape in a hurry; the tape tangles around his wing and sticks to his beak. He shakes it off, getting more flustered.",
      framing="medium shot on Milo at the table", camera="static",
      lines=[], sound="SFX: fast tape screech, sticky 'thwip', frustrated grunts. Music: tense pizzicato."),
 dict(id="S18", dur=6, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo yanks the tape off the blue blade too hard; the rip gets much bigger and the blade hangs half off.",
      framing="close-up on the blue blade and Milo's wings", camera="static",
      lines=[], sound="SFX: long RRRRIP. Music stops."),
 dict(id="S19", dur=6, kind="HOLD", who="M", set="porch", wm="worse",
      action="Milo freezes, staring at the torn blade, beak open, eyes wide; his tuft droops.",
      framing="close-up on Milo's face", camera="very slow push in, hold",
      lines=[], sound="Silence. One soft breeze."),
 dict(id="S20", dur=8, kind="STILL", who="MP", set="porch", wm="worse",
      action="Quiet moment: wide shot of the porch, both friends standing still apart from each other, the torn blade fluttering a little, one leaf drifting past.",
      framing="wide shot", camera="slow push in over a still image; animate only the fluttering blade and leaf if possible",
      lines=[], sound="No music. Soft breeze and a far-off bird only."),
 dict(id="S21", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo drops the tape on the floor and stomps both boots, feathers ruffled.",
      framing="medium shot", camera="static",
      lines=[("Milo", "Grrr! I don't like this windmill anymore!")], sound="SFX: tape roll bounces and rolls away, two stomps."),
 dict(id="S22", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo sits down hard on the porch step with his back to Pip, hugging the torn blade tight and crumpling its edge, shoulders up by his ears.",
      framing="medium shot from the side", camera="slow push in",
      lines=[("Narrator", "Milo felt hot and tight inside. That feeling is frustration.")], sound="Music: slow, low, gentle."),
 dict(id="S23", dur=7, kind="HOLD", who="P", set="porch", wm="worse",
      action="Pip looks down at her paws still holding the windmill stick, then over at Milo; her ears droop and she sniffs quietly.",
      framing="close-up on Pip", camera="static, hold",
      lines=[], sound="SFX: tiny sniff. Music: soft single piano notes."),
 dict(id="S24", dur=8, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip sets the windmill gently in the flowerpot, sits down on the step a little way from Milo and speaks softly.",
      framing="two-shot on the step, a gap between them", camera="static",
      lines=[("Pip", "Milo? Pause. Breathe. Tell me.")], sound="Music: the soft 'Pause. Breathe.' motif (three gentle chimes), first time."),
 dict(id="S25", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo shakes his head without turning around, wings pressed to his round tummy.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "I can't. My tummy is too windy.")], sound="SFX: little tummy 'whoosh' (playful, soft)."),
 dict(id="S26", dur=8, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip nods kindly, scoots a little further back to give Milo space, and sits quietly with her paws in her lap.",
      framing="wide two-shot", camera="static",
      lines=[("Pip", "Okay. I'll be right here.")], sound="Music: very soft pad. SFX: breeze settles."),
 # ---------------- 2:45-4:15 THE TURNING POINT
 dict(id="S27", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Milo peeks over his shoulder at Pip; Pip sits quietly, ears drooping, her scarf moving slightly in the breeze.",
      framing="over-the-shoulder from behind Milo toward Pip", camera="slow push in on Pip",
      lines=[], sound="Silence except soft breeze."),
 dict(id="S28", dur=7, kind="HOLD", who="M", set="porch", wm="worse",
      action="Milo's eyes soften; his tight grip loosens and the crumpled blue blade slowly opens in his wings.",
      framing="close-up on Milo's face and wings", camera="static, hold",
      lines=[("Narrator", "Milo saw Pip's droopy ears. Pip felt sad too.")], sound="Music: soft warm note returns."),
 dict(id="S29", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo looks down at his own wings, then places them on his tummy, remembering.",
      framing="medium close-up on Milo", camera="static",
      lines=[], sound="Music: 'Pause. Breathe.' chimes, very soft (memory)."),
 dict(id="S30", dur=8, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo closes his eyes and whispers to himself, then takes one big slow breath: his round body puffs up big and then slowly settles down.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "Pause. Breathe. Tell me.")], sound="SFX: slow inhale and long exhale. Music: chimes.", caption="TAKE A BREATH (pill, lower third, 3 s)"),
 dict(id="S31", dur=8, kind="GEN", who="MP", set="porch", wm="worse",
      action="Milo takes a second big breath; in the background Pip quietly breathes along with him. The grass outside stops swaying and the light gets warmer.",
      framing="wide two-shot", camera="slow push in",
      lines=[], sound="SFX: two breaths in sync. Wind fades to stillness. Music: warm pad."),
 dict(id="S32", dur=6, kind="STILL", who="MP", set="porch", wm="worse",
      action="Both friends sit on the step; Milo looks at Pip, thinking.",
      framing="two-shot", camera="slow push in over a still image",
      lines=[("Narrator", "What could Milo say to Pip?")], sound="Music: soft tick-tock bed starts.", note="Viewer question (the only one)."),
 dict(id="S33", dur=6, kind="HOLD", who="M", set="porch", wm="worse",
      action="Milo thinks, a small thought bubble with three dots above his head.",
      framing="medium close-up on Milo", camera="static, hold",
      lines=[], pause=4.0, sound="Music: soft tick-tock bed. [PAUSE 4 s for viewers to answer]", note="Thought-dots icon added in edit."),
 dict(id="S34", dur=8, kind="GEN", who="MP", set="porch", wm="worse",
      action="Milo scoots along the step until he is next to Pip and looks up at her; Pip turns and nods.",
      framing="two-shot", camera="static",
      lines=[("Milo", "Pip? Can I tell you something?")], sound="SFX: little scoot on wood."),
 dict(id="S35", dur=6, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo looks at the windmill in the flowerpot, holding the torn blue blade gently now.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "I was so proud of our windmill.")], sound="Music: gentle, warm."),
 dict(id="S36", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo puffs up a little as he remembers being mad, then lets the puff out.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "When it ripped, I got mad. Really mad.")], sound=""),
 dict(id="S37", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo holds up the torn blade and looks at the big rip, a little embarrassed.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "Then I rushed, and I made it worse.")], sound="SFX: soft paper flutter."),
 dict(id="S38", dur=6, kind="GEN", who="P", set="porch", wm="worse",
      action="Pip listens and gives a small, kind smile.",
      framing="close-up on Pip", camera="static",
      lines=[("Pip", "That's a lot of mad.")], sound=""),
 dict(id="S39", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Milo nods and spreads his wings wide to show how big; both giggle a little.",
      framing="two-shot", camera="static",
      lines=[("Milo", "A whole windmill full of mad!")], sound="SFX: small shared giggle."),
 # ---------------- 4:15-5:40 THE PAYOFF
 dict(id="S40", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Milo turns to face Pip properly and looks her in the eyes.",
      framing="two-shot, slightly closer", camera="slow push in",
      lines=[("Milo", "I'm sorry I said you let go.")], sound="Music: warm theme, very soft."),
 dict(id="S41", dur=7, kind="GEN", who="M", set="porch", wm="worse",
      action="Milo points gently at Pip's paws, the ones that held the stick.",
      framing="medium close-up on Milo", camera="static",
      lines=[("Milo", "You didn't. You held on the whole time.")], sound=""),
 dict(id="S42", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip's ears pop back up; she smiles and gives Milo a quick hug.",
      framing="two-shot", camera="static",
      lines=[("Pip", "Thank you for telling me.")], sound="SFX: soft hug 'fwump', ears 'boing'. Music: warm theme rises."),
 dict(id="S43", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip holds up the windmill; Milo nods slowly and carefully.",
      framing="two-shot", camera="static",
      lines=[("Pip", "Want to fix it together? Slowly?"), ("Milo", "Slowly.")], sound=""),
 dict(id="S44", dur=7, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip pulls a small rainbow-striped paper scrap out of the craft box on the table; Milo gasps happily.",
      framing="medium two-shot at the table", camera="slow push in",
      lines=[("Pip", "Look! Rainbow paper!")], sound="SFX: sparkle chime."),
 dict(id="S45", dur=8, kind="GEN", who="MP", set="porch", wm="worse",
      action="Pip holds the torn blue blade flat on the table; Milo smooths the rip closed with careful, gentle wing pats.",
      framing="close-up on the table, paws and wings", camera="static",
      lines=[], sound="Music: gentle building theme (slow version). SFX: soft pats."),
 dict(id="S46", dur=7, kind="GEN", who="M", set="porch", wm="patched",
      action="Milo slowly presses the rainbow patch over the rip and smooths it down.",
      framing="close-up on Milo's wings and the blade", camera="static",
      lines=[("Milo", "Slow... and gentle.")], sound="SFX: soft press, small sparkle."),
 dict(id="S47", dur=6, kind="GEN", who="MP", set="porch", wm="patched",
      action="Together they lift up the mended windmill; the rainbow patch shines on the blue blade.",
      framing="two-shot", camera="static",
      lines=[("Pip", "It looks even better now.")], sound="SFX: sparkle."),
 dict(id="S48", dur=6, kind="GEN", who="MP", set="porch", wm="patched",
      action="They push the windmill stick into the flowerpot on the railing and step back. The tall grass starts to bend.",
      framing="medium-wide two-shot", camera="static",
      lines=[], sound="SFX: the WIND MOTIF begins, the same rising wind as 0:00."),
 dict(id="S49", dur=7, kind="GEN", who="MP", set="porch", wm="patched",
      action="The gust arrives: Milo's feathers and Pip's ears and scarf blow back. Milo reaches for Pip's paw instead of the windmill, and they hold paws while the windmill starts to turn.",
      framing="wide two-shot with the windmill in the foreground", camera="static",
      lines=[], sound="SFX: same big gust 'whoosh' as S02, but no rip. Music: builds."),
 dict(id="S50", dur=8, kind="GEN", who="", set="porch", wm="patched",
      action="The windmill spins faster and faster; the rainbow patch blurs into a rainbow ring. Nobody speaks; viewers just watch it spin.",
      framing="close-up on the spinning windmill", camera="slow push in",
      lines=[], sound="SFX: happy whirr. Music: full warm theme."),
 dict(id="S51", dur=8, kind="GEN", who="MP", set="porch", wm="patched",
      action="Reaction: both friends' faces light up in the wind; Milo bounces on his boots, Pip's ears flap.",
      framing="two-shot, faces large", camera="static",
      lines=[("Milo", "It spins!"), ("Pip", "We fixed it!")], sound="SFX: cheer chime, whirr continues."),
 # ---------------- 5:40-6:00 CLOSING
 dict(id="S52", dur=7, kind="GEN", who="MP", set="porch", wm="patched",
      action="A last puff of wind blows Pip's green scarf right over Milo's face; he wiggles under it and both laugh.",
      framing="two-shot", camera="static",
      lines=[("Milo", "Pip! Your scarf!")], sound="SFX: scarf flap, muffled duck squeak, both laugh."),
 dict(id="S53", dur=7, kind="GEN", who="MP", set="porch", wm="patched",
      action="Milo pulls the scarf off his face, smiles at Pip, and they sit side by side with the windmill spinning behind them.",
      framing="two-shot", camera="slow push in",
      lines=[("Milo", "When I'm mad, I can stop and tell you.")], sound="Music: theme outro."),
 dict(id="S54", dur=6, kind="STILL", who="MP", set="porch", wm="patched",
      action="End card: wide shot of the porch at golden hour, the windmill spinning, Milo and Pip waving.",
      framing="wide shot", camera="slow pull back over a still image (animate the windmill spin in edit)",
      lines=[], sound="Music: theme outro, fade out over the last 3 s.", caption="PAUSE. BREATHE. TELL ME. (pill, center, last 5 s)",
      note="Leave room for YouTube end-screen elements (they need at least 5 s)."),
]

def mmss(s): return f"{s // 60}:{s % 60:02d}"

def words(t): return len(re.findall(r"[A-Za-z']+", t))

def need(sh):
    return sum(words(t) / WPS + BREATH for _, t in sh["lines"]) + sh.get("pause", 0)

def who_line(w):
    return {"M": MILO + ".", "P": PIP + ".", "MP": f"{MILO}, and {PIP}.", "": ""}[w]

def gen_dur(d):
    return (d, None) if d >= 5 else (5, d)

def prompt(sh):
    if sh["kind"] == "REUSE":
        return None
    who = who_line(sh["who"]) or "No characters."
    setting = SETS[sh["set"]] + (f"; {WM[sh['wm']]}" if sh.get("wm") else "")
    g, trim = gen_dur(sh["dur"])
    speech = "Characters talk with gentle mouth movement." if any(w in ("Milo", "Pip") for w, _ in sh["lines"]) else "No dialogue, no lip-sync."
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
    recurring = [s["id"] for s in SHOTS for _, l in s["lines"] if "Pause. Breathe. Tell me." in l]
    assert len(recurring) == 2, recurring
    q = [s["id"] for s in SHOTS for _, l in s["lines"] if "What could Milo say to Pip?" in l]
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
    acts = {"S01": "HOOK (0:00–0:15)", "S05": "WHY IT MATTERS (0:15–1:15)", "S14": "THE PROBLEM GETS BIGGER (1:15–2:45)",
            "S27": "THE TURNING POINT (2:45–4:15)", "S40": "THE PAYOFF (4:15–5:40)", "S52": "CLOSING (5:40–6:00)"}
    for s in SHOTS:
        if s["id"] in acts: out.append(f"\n### {acts[s['id']]}\n")
        out.append(f"\n**{mmss(s['start'])} · {s['id']}** *{s['action']}*")
        if not s["lines"] and not s.get("pause"):
            out.append("  \n[SILENT]")
        for who, line in s["lines"]:
            delivery = ""
            if s["id"] == "S30": delivery = " (whispering to himself)"
            if s["id"] == "S03": delivery = " (blurting)"
            if s["id"] in ("S24", "S26", "S38"): delivery = " (softly)"
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
               f"\"Pause. Breathe. Tell me.\" appears exactly twice ({recurring[0]} Pip, {recurring[1]} Milo). "
               f"The viewer question is asked once ({q[0]}) with a 4 s pause before Milo speaks again in S34.")
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
