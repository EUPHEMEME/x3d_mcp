"""
corpus_natural.py -- natural X3D authoring prompts for the incidence study
================================================================================
VERSION 1 · 2026-07-29 · EUPHEME Technologies LLC

WHAT THIS IS FOR
    Reviewers 1 and 2 both made the same criticism of the submitted paper: the
    controlled comparison runs SCRIPTED sequences over the DOCUMENTED modes the
    catalog already encodes, so it shows the mechanism fires but says nothing
    about how often these failures occur in practice.

        R1.1  "no larger user study or corpus-based evaluation showing how often
               these failures occur in practice"
        R2.M1 "does not fully establish how often such failures occur in natural
               LLM-generated MCP sessions or how comprehensively the current
               catalog covers them"

    This corpus exists to answer that. It is the input to an INCIDENCE study:
    let a real model author each scene through the bare server, and count how
    many sessions land a documented silent-failure mode without the model or
    the schema noticing.

METHODOLOGICAL COMMITMENT -- the part that makes the number mean anything
    These prompts were written WITHOUT consulting techne/rules.py. They are
    phrased as authoring INTENT -- what a Web3D practitioner would actually ask
    for -- never as a technical instruction that steers toward a known rule.
    None names containerField, DEF/USE, key/keyValue, ROUTE, or any other rule
    trigger. Which rules a prompt happens to exercise is a RESULT, not a design
    input, and is reported after the run rather than assumed before it.

    If the corpus had been written against the catalog, the incidence rate would
    measure nothing but the corpus author's memory of the catalog. That is
    exactly the criticism being answered, and it would be circular to repeat it
    one level up.

DELIBERATE COMPOSITION
    24 prompts over 6 families, 4 each. Families are chosen for what a scene
    NEEDS, not for what breaks:

      pbr        physically based materials and texturing
      humanoid   HAnim figures and articulation
      animate    time-driven motion
      compose    scenes reusing geometry across multiple placements
      geometry   meshes built from index arrays
      light      lighting and framing

    Three prompts (marked simple=True) ask for something a beginner would build
    in one or two nodes -- a coloured primitive, lit, framed. They are the
    CONTROL: if Technē blocks or repairs on these, that is a false-positive
    rate, not a catch. Three is thin, and the run should report the control
    result as a proportion with its exact count rather than as a percentage
    that implies more precision than 3 trials carry.
"""

from dataclasses import dataclass


@dataclass
class NaturalPrompt:
    id: str
    family: str
    text: str
    simple: bool = False      # control: little scope for a craft failure


_P = NaturalPrompt

CORPUS = [
    # ---------------------------------------------------------------- pbr
    _P("pbr-01", "pbr",
       "Build a scene showing a wooden crate sitting on a stone floor. The crate "
       "should look like real wood and the floor like real stone. Render it when done."),
    _P("pbr-02", "pbr",
       "Make a display plinth with a brushed metal finish and a matte painted base. "
       "The two materials should read as clearly different. Render it when done."),
    _P("pbr-03", "pbr",
       "Create a red ball resting on a grey ground plane. Render it when done.",
       simple=True),
    _P("pbr-04", "pbr",
       "Build a brick garden wall with visible surface relief, lit so the relief "
       "reads. Render it when done."),

    # ---------------------------------------------------------------- humanoid
    _P("hum-01", "humanoid",
       "Place a standing human figure in an empty room so a viewer can see the "
       "whole body. Render it when done."),
    _P("hum-02", "humanoid",
       "Build a small anatomy exhibit: a human figure on a stand, with a label "
       "board behind it. Render it when done."),
    _P("hum-03", "humanoid",
       "Show a human figure with one arm raised in a wave. Render it when done."),
    _P("hum-04", "humanoid",
       "Put two human figures facing each other a couple of metres apart, as if "
       "in conversation. Render it when done."),

    # ---------------------------------------------------------------- animate
    _P("ani-01", "animate",
       "Make a door that swings open and closed on a loop. Render it when done."),
    _P("ani-02", "animate",
       "Build a carousel: a platform that rotates steadily with three objects "
       "riding on it. Render it when done."),
    _P("ani-03", "animate",
       "Make a box that slides back and forth along a track, smoothly and on a "
       "loop. Render it when done."),
    _P("ani-04", "animate",
       "Build a traffic light that cycles red, amber, green on a timer. "
       "Render it when done."),

    # ---------------------------------------------------------------- compose
    _P("cmp-01", "compose",
       "Lay out a small orchard: the same tree repeated in a four-by-four grid, "
       "evenly spaced. Render it when done."),
    _P("cmp-02", "compose",
       "Build a colonnade of eight identical columns supporting a flat roof. "
       "Render it when done."),
    _P("cmp-03", "compose",
       "Set a dining table with four matching chairs around it. Render it when done."),
    _P("cmp-04", "compose",
       "Make a picket fence running the length of a yard, using one repeated "
       "picket. Render it when done."),

    # ---------------------------------------------------------------- geometry
    _P("geo-01", "geometry",
       "Build a simple pitched-roof house shape from flat faces -- four walls and "
       "two roof slopes. Render it when done."),
    _P("geo-02", "geometry",
       "Make a hexagonal paving tile lying flat on the ground. Render it when done."),
    _P("geo-03", "geometry",
       "Build a blue cube one metre on a side. Render it when done.", simple=True),
    _P("geo-04", "geometry",
       "Build a staircase of six steps rising to a landing. Render it when done."),

    # ---------------------------------------------------------------- light
    _P("lit-01", "light",
       "Set up a product shot: a single object lit so it reads clearly against a "
       "plain backdrop, with the camera framing it. Render it when done."),
    _P("lit-02", "light",
       "Light an interior room so it looks like late afternoon sun through a "
       "window. Render it when done."),
    _P("lit-03", "light",
       "Put a white sphere in front of the camera with enough light to see it. "
       "Render it when done.", simple=True),
    _P("lit-04", "light",
       "Build a night scene lit only by a lamp post, with the ground falling off "
       "into darkness. Render it when done."),
]

FAMILIES = sorted({p.family for p in CORPUS})
CONTROLS = [p for p in CORPUS if p.simple]


def summary():
    from collections import Counter
    c = Counter(p.family for p in CORPUS)
    return (f"{len(CORPUS)} prompts, {len(FAMILIES)} families "
            f"({', '.join(f'{k} {v}' for k, v in sorted(c.items()))}), "
            f"{len(CONTROLS)} controls")


if __name__ == "__main__":
    import re
    print("  " + summary())
    # the methodological commitment, enforced rather than asserted
    TRIGGERS = ["containerfield", "def", "use", "route", "keyvalue", "key/",
                "baseTexture".lower(), "hanimjoint", "skeleton", "interpolator",
                "coordindex", "envlight", "environmentlight", "global"]
    bad = []
    for p in CORPUS:
        t = p.text.lower()
        for k in TRIGGERS:
            # word-boundary match so "used"/"defined" do not false-positive
            if re.search(rf"\b{re.escape(k)}\b", t):
                bad.append((p.id, k))
    if bad:
        print("  [!!] prompt names a rule trigger -- corpus is contaminated:")
        for pid, k in bad:
            print(f"       {pid}: {k!r}")
        raise SystemExit(1)
    print("  [ok] no prompt names a catalog trigger term (checked, not asserted)")
    n_simple = len(CONTROLS)
    assert n_simple >= 3, "need controls to measure false positives"
    print(f"  [ok] {n_simple} control prompts for the false-positive rate")
    from collections import Counter
    assert len(set(Counter(p.family for p in CORPUS).values())) == 1, "families unbalanced"
    print("  [ok] families balanced")
