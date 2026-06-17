# The provenance bridge

*Where the caves work and Technē meet. A working prototype (`techne/provenance.py`,
11 tests) that enforces the documented/interpretive honesty discipline as
deterministic checks — and the decision it puts in front of you.*

## What it is

Technē already turns documented X3D **craft** into mechanism (a wrong containerField
is blocked, not just discouraged). The bridge points the same machine at the
documented **provenance** discipline the caves project produced: it makes the cave
brief's honesty contract *mechanical* rather than a convention a tired author can
forget. It is a deliberate **scope extension** — from "does it render right?" to
"is it honestly sourced?" — so it lives in its own module (`provenance.py`), not in
the core craft catalog.

## The convention (already designed)

The bridge does **not** invent a vocabulary — it enforces the standardized X3D
provenance metadata from `docs/provenance-metadata-proposal.md` (the Web3D AI-X3D
WG deliverable). Each cataloged asset carries X3D's own metadata facility:

```xml
<Transform DEF="SlothHero">
  <MetadataSet name="provenance" reference="https://www.web3d.org/specifications/provenance/1.0">
    <MetadataString  name="provenance"       value='"documented"'/>   <!-- |interpretive|generated -->
    <MetadataString  name="catalogId"        value='"F2"'/>           <!-- key into the asset ledger -->
    <MetadataString  name="sourceCitation"   value='"Stock 1925, Fig. 4"'/>
    <MetadataBoolean name="publicDomain"     value="true"/>
    <MetadataString  name="generationMethod" value='"trace:potrace; no-AI-imagery"'/>
  </MetadataSet>
  <!-- the asset's geometry -->
</Transform>
```

`catalogId` keys into an **asset ledger** — `drawings/archive.json` shape:
`{entries: [{id, citation, source_url, public_domain, ...}]}`. It travels *in the
scene graph*, so provenance survives export, unlike a sidecar JSON or a code comment.

## What Technē checks now — Layer 1 (sourcing), built + tested

`check_scene_provenance(xml, ledger)` parses every `MetadataSet name='provenance'`
block and applies five deterministic rules (the message *is* the correction):

| rule | fires when | enforces |
|---|---|---|
| `provenance_documented_uncited` | `documented` with no `catalogId`/`sourceCitation` | *you cannot label a feature documented until you have the page that documents it* |
| `provenance_catalogid_unresolved` | `catalogId` not in the ledger | every documentary claim resolves to a cataloged asset |
| `provenance_not_public_domain` | resolved asset is not `public_domain` | no AI imagery / no uncleared assets presented as record |
| `provenance_generated_undisclosed` | `generated` with no `generationMethod` | AI/derived geometry must disclose itself |
| `provenance_invalid_status` | not documented\|interpretive\|generated | the tag is well-formed |

Demonstrated against the real `archive.json` (11 cataloged assets): a documented
sloth citing `F2` (public-domain) passes; an `interpretive` speleothem passes
(unconstrained by design); an uncited "documented" column and an undisclosed
"generated" texture are blocked. This layer is **general** — it works for any
documentary X3D corpus, which is exactly the Web3D *curated-repository-with-rich-
metadata* goal.

## What it does NOT check yet — Layer 2 (content semantics)

The `must_not_invent` clauses split in two. Layer 1 above covers the **sourcing**
ones. The rest are **content-semantic**: *"don't pin a taxon to a depth,"
"Euceratherium type is Samwel not Potter Creek," "Samwel depth ≠ age," "ages are
cal BC."* Technē cannot check these from a `provenance` tag alone — they need
**structured claim fields** (e.g. `taxon`, `depth`, `unit`, `dateBasis`) and rules
over them. That is a domain-specific "fossil-claim" schema that *builds on* Layer 1,
and it is heavier (a vocabulary per domain). Layer 1 is the reusable spine; Layer 2
is opt-in per corpus.

## Wiring — deliberately not automatic yet

`check_scene_provenance` is a library function. It is **not** wired into the proxy,
because the gate needs two things that are your call: a **configured ledger** and a
scene that actually **carries the metadata**. Once both exist, the hookup is one
block in the occupation gate / a render post-pass (the same shape as the blank-render
warning): fetch the scene XML, run the check, and on a hard violation *withhold
sign-off* — provenance becomes an enforced gate, not a hope.

## The decision in front of you

1. **Bless the vocabulary** (the `provenance.py` rules ≈ the proposal's table) as the
   convention Technē enforces — or amend it.
2. **Adopt it in the cave pipeline**: have `generate_cave.py` / `generate_samwel.py` /
   `generate_fauna_strata.py` emit the `MetadataSet` blocks (they already hold the
   documented/interpretive split in comments + captions — this moves it into the graph).
3. **Wire the gate** (opt-in via `TECHNE_ASSET_LEDGER`), so a scene with an unsourced
   "documented" claim cannot pass.
4. **Decide on Layer 2** — whether to build the domain claim-schema for the content
   `must_not_invent` rules, or leave provenance at the (reusable, general) sourcing layer.

My recommendation: ship Layer 1 (it's done and general, and it's the Web3D metadata
goal made mechanical), adopt it in the cave pipeline next, and treat Layer 2 as a
separate, clearly-scoped follow-on rather than folding it in now.
