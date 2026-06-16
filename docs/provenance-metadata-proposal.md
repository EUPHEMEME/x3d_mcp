# Provenance and Metadata for AI-Authored 3-D: A Proposal for Curated Training Repositories

*A working proposal for the Web3D AI-X3D Working Group's "curated training repositories with rich metadata" and "metadata vocabularies" goals.*

Author: Alexander Hoffman (GitHub `EUPHEMEME`, alex@euphe.me). This document was drafted with the assistance of Anthropic's Claude (Claude Code) operating as a tool under the author's direction; per the ACM Policy on Authorship the AI is not an author. Its use is disclosed here and credit is the human author's.

Grounded in the working model at `drawings/archive.json`, `drawings/ARCHIVE.md`, and `drawings/strata_spec.json` in `github.com/EUPHEMEME/x3d_mcp` (branch `potter-creek-cave`). Live viewers and papers: https://euphememe.github.io/shasta-caves/

---

## 1. The problem: without provenance, a plausible 3-D model is a falsified record

A language model that authors X3D produces geometry that *looks* surveyed, *looks* measured, *looks* drawn from life. It is fluent precisely where it is unaccountable. A rendered cave, a posed skeleton, a stratigraphic column all carry the same visual authority whether they trace a published 1904 survey plate or were confabulated wholesale a moment ago. The medium erases the difference; the viewer cannot see it.

This is not a stylistic concern. For any 3-D scene that purports to represent something real — a dig site, a specimen, a building, a terrain — an unlabeled AI-generated asset is indistinguishable from a faithful record, which means it *competes with* and can *contaminate* the genuine record. A plausible fabrication, once it enters a "curated training repository," becomes training signal: the next model learns that this is what a Pleistocene cave deposit looks like, and the fabrication propagates with compounding authority. The failure mode of AI 3-D is not ugliness. It is confident, well-formed, untraceable assertion.

The Working Group's own goals name the antidote without quite naming the requirement: **curated training repositories with rich metadata**. The claim of this proposal is narrow and concrete: *for 3-D assets, the load-bearing metadata is provenance.* A repository curated for training must be able to state, per asset and machine-readably, what each thing is a record **of**, where that record came from, and which parts are documented versus interpreted. Otherwise "curated" guarantees only that the fabrications are well-formed.

## 2. Our concrete model: documented vs. interpretive, per-asset citation, no invented geometry

The Potter Creek and Samwel Caves archive is a worked example of a provenance-disciplined 3-D corpus built *with* an LLM authoring pipeline. It is small, fully cited, and deliberately conservative. Its discipline reduces to a handful of rules that are already enforced in our data, not aspirations:

**Trace, don't invent.** Every base asset is a faithful vector trace of a real published drawing, produced by a deterministic pipeline (`trace_drawing.sh`: `pdftoppm` → crop → threshold → `potrace` → SVG; then `svg_to_x3d.py` / `extrude_contours.py` to to-scale X3D). The pipeline has no generative step. There is **no AI imagery and no invented geometry** anywhere in the corpus. The stated principle in `archive.json` is verbatim: *"Every item is a faithful vector trace of a real published drawing, fully cited. No AI imagery; no invented geometry."*

**Per-asset citation, source, and public-domain status.** Each catalog entry in `archive.json` carries: a `subject`, a full bibliographic `citation` (down to plate/figure/page — e.g. *Sinclair 1904, Plate 14, contour interval 6 inches*), a resolvable `source_url` (Berkeley anthpubs, archive.org, BHL), a `public_domain` flag, the intermediate `trace` artifact, and the resulting `x3d` files. Derived assets cite their derivation explicitly (A5: *"contours lifted by nesting depth × the surveyed 6-inch interval and triangulated"*).

**A documented-vs-interpretive tag, applied per claim, not per file.** This is the crux. Provenance is not a file-level checkbox; a single scene mixes documented and interpreted content. In `strata_spec.json` every stratum and every faunal marker carries an explicit `status` of `documented` or is flagged interpretive, with the citation that backs it. The Shasta ground-sloth skeleton is real published anatomy (Stock 1925, Fig. 4) but its *placement* is unprovenanced, so it is flagged **interpretive, unprovenanced** and made to float beside the column, *never embedded in a stratum*. Fauna are pinned **only where the literature gives a depth**; the mixed assemblage gets one honest marker (*"fauna occur throughout the bone-bearing clay and breccia — not depth-sorted,"* Sinclair 1904 p.19, *"the fauna listed is a unit"*).

**An explicit negative space — what must not be invented.** `strata_spec.json` carries a `must_not_invent` array: twelve enumerated claims the data is forbidden to assert (no per-taxon depths for the 52-species list; no measured depth for Cope's *Arctotherium* type skull; cal BC not cal BP for Samwel; the Samwel dated specimens tagged by square+inch are *not* to be mapped onto named lithologic units). This encodes provenance as a *constraint on generation*, which is exactly the form a training repository needs: the corpus says not only what is true but what may not be claimed.

**Machine-readable, citation-anchored.** `archive.json` is the catalog; `strata_spec.json` is the citation-anchored stratigraphy. Both are JSON today, sidecar to the X3D. The proposal below moves this same content *into* the X3D scene graph as standardized metadata so it travels with the asset.

## 3. How this plugs into the WG's curated-repo and X3D-Edit metadata efforts

The Working Group lists, as goals, *curated training repositories with rich metadata*, *MCP for asset cataloging*, *metadata vocabularies*, and *ethical considerations / best practices*. Our model maps onto these directly and suggests specific, small standardization targets.

**For the curated training repository.** Adopt provenance as a *required* metadata facet for any asset admitted to a training corpus, and make `provenance=documented|interpretive|generated` a first-class, machine-readable field. A corpus curated this way is filterable: a training run that wants only ground-truth survey records can exclude `interpretive` and `generated`; a run that wants to teach interpretation-with-disclosure can keep them *with their labels intact* so the model learns the disclosure too. This is the difference between a repository that launders fabrication and one that teaches accountability.

**For X3D-Edit and the metadata vocabulary.** X3D already has the carrier — `MetadataString`, `MetadataSet`, `MetadataBoolean`, the `metadata` field on every node — but no agreed *vocabulary* for provenance. The leverage is in standardizing a small set of `MetadataSet` `name`/`reference` terms so that X3D-Edit, X_ITE/X3DOM, and validators all read provenance the same way. Concretely, terms worth standardizing (`reference` = a stable vocabulary URI):

| Term | Values / type | Meaning |
|---|---|---|
| `provenance` | `documented` \| `interpretive` \| `generated` | the load-bearing tag, per scene and per asset |
| `sourceCitation` | string (free bibliographic) | full citation to plate/figure/page |
| `sourceURL` | URI | resolvable scan/source |
| `license` | SPDX-style string | e.g. `CC0-1.0`, `public-domain` |
| `publicDomain` | boolean | jurisdiction-qualified PD status |
| `generationMethod` | string | e.g. `trace:pdftoppm+potrace`, `derived:extrude_contours`, `llm:<model>` |
| `derivedFrom` | string / IDREF | the asset or citation this was derived from |
| `mustNotInvent` | string (per scene) | enumerated forbidden claims |

**For MCP asset cataloging and Technē.** Because the catalog already exists as JSON, an MCP cataloging tool can emit these `MetadataSet` blocks deterministically, and a craft layer (our Technē man-in-the-middle on the x3d-mcp server) can *gate* on them: refuse to sign off a scene whose top node lacks a `provenance` tag, or whose `generated` geometry is presented without disclosure. Provenance then becomes an enforced occupation gate, not a convention one hopes authors honor.

## 4. A proposed minimal provenance vocabulary, with X3D examples

The aim is the smallest schema that captures what `archive.json` and `strata_spec.json` already encode, expressed natively in X3D so it travels in the scene graph. Two levels: **scene-level** (one block per file, on the `Scene` or `WorldInfo`) and **asset-level** (one block per `Transform`/`Shape`/`Group` that constitutes a distinct cataloged asset). Provenance is per-claim where needed via nested asset blocks — matching our rule that a single scene mixes documented and interpretive content.

### 4.1 Scene-level provenance

```xml
<Scene>
  <WorldInfo title="Potter Creek Cave — bone-horizon section (A6)">
    <MetadataSet name="provenance"
                 reference="https://www.web3d.org/specifications/provenance/1.0">
      <MetadataString name="provenance" value='"documented+interpretive"'/>
      <MetadataString name="catalogId" value='"A6"'/>
      <MetadataString name="sourceCitation"
        value='"Sinclair, W.J. (1904) The Exploration of the Potter Creek Cave, UCPAAE 2(1):1-27; Payen &amp; Taylor (1976) J. Calif. Anthropology 3(1):51-58."'/>
      <MetadataString name="sourceURL"
        value='"https://digitalassets.lib.berkeley.edu/anthpubs/ucb/text/ucp002-003.pdf"'/>
      <MetadataString name="license" value='"public-domain"'/>
      <MetadataBoolean name="publicDomain" value="true"/>
      <MetadataString name="generationMethod"
        value='"trace:pdftoppm+potrace; derived:extrude_contours; no-AI-imagery"'/>
      <MetadataString name="mustNotInvent"
        value='"No per-taxon depths for the 52-species list (Sinclair p.19: the fauna is a unit); no measured depth for Cope&apos;s Arctotherium type skull."'/>
    </MetadataSet>
  </WorldInfo>
  <!-- geometry follows -->
</Scene>
```

### 4.2 Asset-level provenance — a documented trace

```xml
<Transform DEF="EuceratheriumDental">
  <MetadataSet name="provenance"
               reference="https://www.web3d.org/specifications/provenance/1.0">
    <MetadataString name="provenance" value='"documented"'/>
    <MetadataString name="catalogId" value='"F1"'/>
    <MetadataString name="subject"
      value='"Euceratherium collinum — left superior dental series"'/>
    <MetadataString name="sourceCitation"
      value='"Sinclair &amp; Furlong (1904) Text Fig. 1, Univ. Calif. Bull. Dept. Geol. 3(20):411-418."'/>
    <MetadataString name="sourceURL"
      value='"https://archive.org/details/bulletinofde319021904univ"'/>
    <MetadataString name="generationMethod" value='"trace:pdftoppm+potrace"'/>
    <MetadataBoolean name="publicDomain" value="true"/>
  </MetadataSet>
  <Shape><!-- IndexedLineSet from euceratherium_dental.svg --></Shape>
</Transform>
```

### 4.3 Asset-level provenance — a flagged interpretive figure

```xml
<Transform DEF="SlothHero">
  <MetadataSet name="provenance"
               reference="https://www.web3d.org/specifications/provenance/1.0">
    <MetadataString name="provenance" value='"interpretive"'/>
    <MetadataString name="catalogId" value='"F2"'/>
    <MetadataString name="subject"
      value='"Nothrotheriops shastensis skeleton — context only, unprovenanced, NOT depth-resolved"'/>
    <MetadataString name="sourceCitation"
      value='"Stock, C. (1925) Cenozoic Gravigrade Edentates, Fig. 4, Carnegie Inst. Publ. 331, p.33. (Real published skeletal drawing; placement is interpretive.)"'/>
    <MetadataString name="derivedFrom" value='"F2-trace"'/>
    <MetadataString name="interpretiveNote"
      value='"Skeleton drawing is documented; its pose/placement beside the column is interpretive. Never embedded in a stratum (strata_spec must_not_invent)."'/>
  </MetadataSet>
  <Shape><!-- floats beside the column, visibly labeled --></Shape>
</Transform>
```

The pattern: `provenance` always present; `documented` requires `sourceCitation`; `interpretive` requires an `interpretiveNote` stating exactly what is documented and what is inferred; `generated` (not used in this corpus) would require `generationMethod` naming the model. A validator can check these conditionals mechanically.

## 5. Next steps

1. **Emit metadata from the existing catalog.** Add a small generator that reads `archive.json` / `strata_spec.json` and writes the `MetadataSet` blocks above into the caves' `.x3d` files — turning the sidecar JSON into in-scene-graph provenance with no new authoring burden. The data already exists; this is serialization.
2. **Publish the vocabulary as a one-page draft.** A short, stable list of the §4 terms with a `reference` URI, offered to the WG and to X3D-Edit as a candidate metadata vocabulary. Keep it minimal; resist scope creep.
3. **Add a provenance validator to the x3d-mcp / Technē craft layer.** Extend the semantic validators (PR #10) with a non-fatal provenance check: warn when a `Scene` or cataloged `Transform` lacks `provenance`, error when `documented` carries no `sourceCitation` or `interpretive` carries no note. Wire it into the render-and-sign-off occupation gate so AI-authored scenes cannot be declared finished without disclosure.
4. **Propose `provenance` as an admission filter for the curated training repository.** Recommend the X3D Example Archives (X3D4AM) record this facet on contributed assets, so corpora are filterable by `documented | interpretive | generated` and the caves archive can be ingested *with its labels intact* as a reference example, alongside its session logs.
5. **Solicit one external review** from the survey/paleo side to confirm the vocabulary is sufficient to round-trip a real citation, before proposing standardization.

This is offered as a modest, concrete starting point, not a finished standard: a small vocabulary, already backed by a working corpus, aimed squarely at keeping curated 3-D training data honest about what it is a record of.
