# build_anatomy/research — the anatomy KB source layer

This directory holds the committed research batches that `../../build_kb.py`
merges into `build_anatomy/anatomy_kb.json` (the explorer's teaching layer),
plus the source-anchored reference corpus and the citation checker that gate
them.

## Batch file schema

Files named `batch_*.json` are merged by `build_kb.py` in filename order
(`glob build_anatomy/research/batch_*.json`); later batches may add bones,
and the manifest-resolution step in `build_kb.py` reports coverage per
`groupFallback` group.

```json
{
  "_provenance": { "origin": "free-text: where this batch came from", "bones": 83 },
  "regions": [
    {
      "group_title": "The Vertebral Column: ...",
      "group_teaching": "one-paragraph region-level teaching text",
      "bones": [
        {
          "name": "c1",                       // manifest name, lowercase (bone_manifest.json)
          "group": "Cervical vertebrae",
          "function": "what the bone does, one teaching paragraph",
          "articulates_with": ["...", "..."],
          "note": "memorable detail / etymology / clinical hook",
          "source": "grays1918:<anchor-text>"  // REQUIRED for batch_001+, see below
        }
      ]
    }
  ]
}
```

## Reference corpus (`ref/`)

- `ref/grays1918.txt` — Gray's *Anatomy of the Human Body*, **20th edition,
  1918** (Lea & Febiger; public domain). Note: this edition is **not** on
  Project Gutenberg (verified 2026-08-31 — Gutenberg has no Henry Gray
  anatomy text); the plain text here is the Internet Archive OCR of the 1918
  printing, item `anatomyofhumanbo1918gray`
  (`https://archive.org/download/anatomyofhumanbo1918gray/anatomyofhumanbo1918gray_djvu.txt`),
  header-verified ("TWENTIETH EDITION ... Copyright LEA & FEBIGER 1918").
  It is OCR text: expect spacing/ligature noise; the checker normalizes for it.
- `ref/ta_terms.txt` — Terminologia Anatomica-style `english | latin | synonyms`
  pairs covering the 256 manifest part names (pattern entries use `{n}` for
  vertebra/rib/phalanx/tooth indices). Extend it when a new bone name or
  synonym is needed; the checker reads it at run time.

## The citation rule (all batches after batch_000)

Every bone entry MUST carry a `source` of the form:

```
"source": "grays1918:<anchor-text>"
```

where `<anchor-text>` is a short verbatim phrase (a section heading or a
distinctive sentence fragment, >= ~4 words is robust against OCR noise) that
occurs in `ref/grays1918.txt` at the passage supporting the entry.
`batch_000_initial83.json` predates the rule — its entries report as UNCITED
(warning), and that is expected; do not fail it retroactively.

## Verification gates (run all three before merging a batch)

1. **Manifest resolution** — `python3 ../../build_kb.py` (from repo root:
   `.venv/bin/python build_kb.py`): every batch bone name must resolve against
   `bone_manifest.json`; the coverage report shows gaps, and `KB_REQUIRE_FULL=1`
   makes gaps fatal.
2. **Citation check** —
   `.venv/bin/python build_anatomy/research/check_citations.py build_anatomy/research/batch_NNN_*.json`
   For each cited entry it verifies (a) the anchor text exists in Gray's 1918
   and (b) the bone's display/Latin/synonym terms (via `ref/ta_terms.txt`)
   appear within +/-6000 chars of the anchor. Any FAIL exits nonzero and blocks
   the merge. UNCITED is a warning only (batch_000).
3. **Human spot-check** — eyes are ground truth (house rule): open the cited
   passage in `ref/grays1918.txt` for a random ~10% sample of new entries and
   read that the claim in `function`/`note` is actually what Gray says. The
   checker proves the citation points somewhere real and on-topic; only a
   human proves it supports the claim.
