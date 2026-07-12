# Point-1, answered: the cross-call automaton is not warranted

The paper defers the cross-call order-of-operations automaton and says why (§4.4):

> A cross-call automaton enforcing order-of-operations over a whole session is
> intentionally absent. Open-ended authoring should resist a straitjacket. The
> likely truth is a partial order — a few hard edges in a large open space — so
> the next step is instrumentation: log the verb order of clean renders, let
> accumulated usage identify real constraints before committing an automaton.

That was the right instinct. This is the measurement, and it says the automaton
should stay unbuilt — not for lack of data, but because **there is nothing for it
to catch**.

## Method: ablation, not observation

`analyze_traces.py` does Point-1 by *observation*: collect sessions, correlate
verb bigrams with clean renders. The trouble is that observation needs a large
corpus and, even then, only reports what models happen to **do** — not what X3D
**requires**. A bigram that never appears may be forbidden, or merely
unfashionable. You cannot tell which, and a constraint learned from the first is
a rule while one learned from the second is a straitjacket.

So `eval/order_ablation.py` runs an *experiment* instead. Take an authoring
program that renders. For each candidate ordering edge A→B, emit the program with
the edge **violated** (B moved before A), run it through the **bare** x3d_mcp — not
Technē; we are measuring what the format requires, not what Technē enforces — and
render the result. Classify by what actually happens:

| verdict | meaning |
|---|---|
| **SILENT** | every call succeeds, the XSD is happy, and the scene renders **wrong or blank**. This is Technē's entire domain, and each one is a candidate rule. |
| **LOUD** | the server refuses. The model already sees the error; the transport *is* the enforcement. |
| **DATAFLOW** | the move is not expressible — B references an id A produces. Not a convention at all. |
| **FREE** | renders identically. The edge is folklore, and legislating it would be a **false positive**. |

Known bugs are controlled for: the raw server never declares
`<component name='HAnim'/>` (Bug 5), so without `reassert_profile` every variant —
baseline included — renders blank and the experiment measures nothing. We are
asking about *order*, so the component bug is a confound to remove, not the thing
under test.

## Result

Three authoring programs (an HAnim humanoid, a ROUTE-driven animation, a DEF/USE
reuse), 14 candidate ordering edges:

```
SILENT    0   ← passes the schema, renders wrong
LOUD      2   ← the server already refuses
DATAFLOW  5   ← ids make the move impossible
FREE      7   ← renders identically
```

**Not one ordering constraint fails silently.** Every real constraint is already
enforced by the transport. Half of the "obvious" conventions are simply free:

- a Shape's appearance need **not** be attached before its geometry;
- a Material need **not** be inside its Appearance before the Appearance is attached;
- an HAnimSegment need **not** be filled before it is joined to its Joint;
- a Viewpoint need **not** be created before the geometry it will frame;
- a Shape need **not** be complete before it is DEF'd for reuse;
- the order of unrelated `create_node` calls does not matter.

An automaton enforcing any of those would produce nothing but false positives.

## Why — and this is the part worth keeping

The result is not luck. It follows from the shape of the tool surface.

**The granular API passes opaque node ids, not names.** `add_child(parent_id,
child_id)`, `set_field(node_id, …)`, `def_node(node_id, …)` — every one of them
refers to a node by an id the server minted. So an ordering constraint over ids is
a **dataflow** constraint: you cannot reference an id you have not created. And
dataflow is enforced by the transport, for free, with no rule and no automaton.

The single place a **name** enters the surface is `use_node(def_name)` — a string,
not an id. That is the one edge on which an ordering violation can even be
*expressed*. So if a silent ordering failure existed anywhere, it should be there.
It is not: the server checks the DEF table eagerly and refuses loudly.

> **An id-passing tool surface makes order-of-operations bugs unrepresentable.**

This is a real design property of MCP-shaped authoring, and it is the reason the
automaton has nothing to do. It also sharpens the paper's own thesis by drawing a
boundary the paper does not currently draw:

- silent failure lives in **arguments** (a dropped `containerField`, a
  non-spec default, a mismatched interpolator arity) — Technē §5;
- and in the **document** (an undeclared component, a dropped profile) — Bug 5,
  the serialization boundary;
- but **not in order**. Order is safe, and it is safe *by construction*.

## An honest consequence for the catalog

Two existing PER_CALL rules — `use_after_def` and `route_no_def` — duplicate a
check the server already performs loudly. They are not *wrong*: Technē's message
is prescriptive where the server's is bare, which is the paper's own distinction.
But they are **not catching silent failures**, and the paper should not let a
reader assume they are. Their value is message quality, not detection.

## Scope

14 edges across 3 programs is not exhaustive, and this cannot prove a negative.
What it establishes is that across the ordering edges an LLM plausibly gets wrong
in these authoring patterns, none is silent — and it gives a method that extends:
add a program, name its candidate edges, and the harness answers them.

```
cd techne && ../.venv/bin/python -m eval.order_ablation
```
