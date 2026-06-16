# Example: A Documented Cave, Verified by Render

A real LLM + MCP X3D authoring flow that builds a **to-scale, citation-anchored**
model of Potter Creek Cave (Shasta County, California; excavated 1903-06 under
John C. Merriam), then drives the canonical **validate -> render -> look** loop
to confirm it. The point of interest for the archive is not the geometry alone
but the **provenance discipline**: every coordinate is either *documented* (traced
from a published survey) or clearly flagged *interpretive*, on-screen and in the
file metadata. No AI imagery, no invented survey geometry.

> **Author / tool disclosure.** This session was conducted by Alexander Hoffman
> (GitHub `EUPHEMEME`). Anthropic's Claude (via Claude Code) was the tool used
> under his direction. Per the ACM Policy on Authorship the model is not an
> author; its use is disclosed and only the human is credited.
>
> **How to read this log.** Blocks marked **[verbatim]** are copied from the
> actual session scrape (`sessions/potter_creek_cave_session.md`, produced by
> `scrape_session.py`). Blocks marked **[illustrative]** are representative
> reconstructions of the same step, shown to make the flow self-contained;
> their tool *outputs* are not invented runtime results.

## Chat

**User:** Build Potter Creek Cave to scale from the Sinclair survey. Keep it
honest -- only put geometry where the report gives a measurement, and flag
anything we add for atmosphere.

### 1. Look up before you build  *[illustrative]*

The server's first rule is *never guess field or containerField names* -- call
`describe_node` first. The model is going to lay the survey out as line/edge
geometry, so it checks the node it intends to use.

**Model calls** `describe_node`:
```json
{ "name": "IndexedLineSet" }
```
**MCP response (abridged):**
```
IndexedLineSet (Rendering component)
  default containerField: geometry   (belongs to a Shape's 'geometry' field)
  coordIndex   MFInt32   polyline point indices, -1 terminates each polyline
  coord        SFNode -> Coordinate  (containerField='coord')
  colorPerVertex / colorIndex / color ...
```
This is the look-up the discipline demands: the model now knows the
`Coordinate` child must carry `containerField='coord'`, which is exactly the
kind of detail the XSD will *not* catch if it is wrong.

### 2. Build from cited measurements, not from imagination

The geometry is emitted by a deterministic generator (`generate_cave.py`),
which is the project's "trace, don't invent" pipeline: hard numbers come
*verbatim* from the published report, 1 X3D unit = 1 foot. The generator opens
with a PROVENANCE block separating documented from interpretive geometry.

**Source header of `generate_cave.py`  [verbatim]:**
```text
Hard numbers used (all verbatim from the report, 1 X3D unit = 1 foot):
  * main chamber: 107 ft long, ~30 ft wide at widest, roof ~75 ft above
    the lowest point of the floor
  * two fan-like breccia deposits sloping from opposite ends and
    coalescing in the middle; near-vertical chimney openings above each apex
  * access by a 42 ft vertical descent (rope ladder) at the great pit
  * galleries trend NW-SE; stratigraphy of the NW fan: upper clay to
    13.5 ft, volcanic ash ~1.5 ft, cemented breccia below
```

The citation and the documented/interpretive split are written into the file's
own metadata so the provenance travels with the scene:

**Emitted `<head>`  [verbatim from generator]:**
```xml
<meta name="title" content="Potter Creek Cave"/>
<meta name="description" content="To-scale model from Sinclair (1904),
  excavation directed by John C. Merriam. Shasta County, California."/>
<meta name="reference" content="Sinclair, W.J. (1904) The Exploration of
  Potter Creek Cave. Univ. Calif. Publ. Amer. Arch. Ethn. 2(1)."/>
<meta name="creator" content="x3d_mcp cave pipeline"/>
```

> Note on method: in this session the geometry came from the generator, not
> from `create_node`/`compose_scene` calls. That is deliberate -- a script that
> reads measurements and emits coordinates is auditable and reproducible in a
> way a free-hand modelling chat is not. The MCP's role here is the part a
> generator *cannot* self-check: schema conformance, semantic/runtime
> correctness, and **whether the thing actually looks right.**

### 3. Validate -- and learn a real tool limitation

**Model calls** `validate_x3d` on the `potter_creek_cave.x3d` **file path**:

**MCP response  [verbatim]:**
```json
{
  "valid": false,
  "errors": [
    "XML parse error: Start tag expected, '<' not found, line 1, column 1"
  ]
}
```

This is *not* a problem with the scene -- it is the tool: `validate_x3d` wants
the X3D *content* inline, not a file path, so it tried to parse the path string
as XML. (A genuine finding, the honest kind a session log should keep: the
schema-validation step was effectively skipped here, and the X_ITE render below
became the real conformance test. The semantic checker, which accepts a path,
ran fine.)

**Model calls** `validate_semantic` on the same file:

**MCP response  [verbatim]:**
```text
# Semantic Check: All Clear

No semantic issues found. The scene looks well-structured.
Note: This checks common authoring issues beyond XSD schema validation.
Use validate_x3d for schema-level validation.
```

**Model:** The semantic layer is clean (the containerField / USE-before-DEF /
ROUTE class of errors that pass the schema but still render black). XSD
validation was skipped due to the path-vs-inline issue above, so the render is
now the decisive check -- render it and actually look.

### 4. Render and look -- the loop catches what validation can't

**Model calls** `render_image` on `potter_creek_cave.x3d`:

**MCP response  [verbatim]:**
```text
Render failed: It looks like you are using Playwright Sync API inside the
asyncio loop. Please use the Async API instead.
```

This is a **real defect**, recorded honestly rather than papered over: at the
time of this session the MCP's `render_image` used the X3DOM + sync-Playwright
backend, which crashes inside the server's asyncio loop -- and, separately,
X3DOM cannot render this project's PBR/HAnim scenes at all. (Closing this gap
with an X_ITE render backend is upstream PR #10.) The model falls back to the
out-of-process X_ITE/puppeteer screenshot the rest of the project uses, so it
can still *see* the scene:

**Model renders two viewpoints and reads the PNGs back  [verbatim, abridged]:**
```text
wrote cave_refs/cave_0.png
wrote cave_refs/cave_1.png
```
**Model (reading `cave_0.png`):** Mostly black -- we're inside an underlit
shell. Let me check the overhead/plan view... **Both black:** a closed shell
reads as a dark blob from outside and is underlit from inside.

This is the entire reason the loop exists. The scene was *valid* and
*semantically clean* and still visually useless. The fix is a viewing decision,
not a validity one:

**Model:** The legible, classic way to show a cave is a **longitudinal section
cut** -- keep the back half, open the front toward the camera so the headlight
floods the interior. *(Edits `generate_cave.py` to a cut-away, re-renders.)*

After the cut-away and a lighting pass, the re-render reads as a believable
cave: domed roof, the entrance fan, the daylight shaft down the pit. Only once
a render is inspected and correct is the scene declared done.

### 5. State the provenance, on the record

With the geometry confirmed, the model writes the documented/interpretive split
explicitly -- in the generator's PROVENANCE block, in the on-screen caption, and
in its summary to the user:

**Model summary  [verbatim, abridged]:**
> **Documented -- to scale from Sinclair (1904):** the 107-ft chamber, ~30-ft
> width, ~75-ft roof; the two breccia fans coalescing mid-chamber; a chimney
> above each fan apex; the 42-ft entrance pit; the NW-fan stratigraphy and the
> NW-SE trend.
>
> **Imaginary -- interpretive cave dressing (plausible, not from the survey):**
> every speleothem (stalactites, stalagmites, columns, flowstone draperies); the
> breakdown blocks on the floor; the standing pools; the daylight shaft, all
> lighting, the rock colouration, and the 6-ft scale figure.
>
> Sinclair mapped the *chamber*, never its formations -- so the geometry you can
> measure is faithful, and everything atmospheric is clearly flagged as
> interpretation.

## What this demonstrates

- **The canonical loop is not optional.** `describe_node` -> build ->
  `validate_x3d` **and** `validate_semantic` -> `render_image` and *look*. Here
  the semantic checker was clean and the schema check was skipped (a tool
  path-vs-inline quirk), yet the scene first rendered black -- only inspecting
  the image surfaced it. Whatever the validators say, the render is the proof.
- **Validation and seeing are different guarantees.** XSD checks shape;
  `validate_semantic` checks the runtime traps a schema can't (containerField,
  USE-before-DEF, ROUTEs); the render is the only thing that proves the scene is
  *legible*.
- **Honest defect reporting.** The `render_image` sync/async crash and X3DOM's
  inability to render PBR/HAnim are recorded as real limitations, with the X_ITE
  backend (PR #10) as the fix -- not hidden behind a staged success.
- **Provenance discipline is machine-readable, not a footnote.** Documented vs.
  interpretive geometry is separated in the generator, stamped into the scene's
  `<meta>` (`reference`, `description`), shown in the on-screen caption, and
  stated to the user. The literature citation travels inside the `.x3d` file.
- **Trace, don't invent.** Coordinates come from a deterministic generator fed
  cited measurements (1 unit = 1 ft), making the model auditable and
  reproducible; no AI-generated imagery or fabricated survey geometry.

## Reproducing this log

These session logs are produced by **`scrape_session.py`**, which renders a
Claude Code JSONL transcript into the project's two standard local records:

```text
sessions/<name>.json   -- the raw JSONL transcript, copied verbatim
sessions/<name>.md     -- a readable markdown render (User / Assistant /
                          tool calls / result blockquotes)
```

Run `python scrape_session.py` to refresh after more conversation. The verbatim
blocks above are drawn from `sessions/potter_creek_cave_session.md`.

## Files

- Generator (provenance + measurements): [`generate_cave.py`](../generate_cave.py)
- Scene: `potter_creek_cave.x3d` (X3D 4.0, X_ITE viewer in `potter_creek_cave_xite.html`)
- Documented-trace generator for survey plates: [`svg_to_x3d.py`](../svg_to_x3d.py)
  (potrace SVG -> `IndexedLineSet`; geometry *is* the traced drawing)
- Session scraper: [`scrape_session.py`](../scrape_session.py)
- Live viewers and papers: <https://euphememe.github.io/shasta-caves/>
