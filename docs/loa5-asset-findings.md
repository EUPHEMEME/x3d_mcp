# Findings in the HAnim `AllBonesLOA5Skeletons` bone-mesh set

Surfaced while building the [LOA5 Anatomy Explorer](../demo-releases/2026-07-12_anatomy-explorer/),
which makes all 257 parts of the LOA-5 skeleton individually pickable. Making every
bone addressable turns out to be a good way to find the ones that aren't there.

Everything below is reproducible from the assets in `assets/loa5/meshes/` (277 files).
Offered to the Web3D Consortium AI-with-X3D / HAnim working group in the spirit of the
existing `docs/x3dpy-bug-report.md`.

---

## 1. `AxesDisplay.x3d` is referenced by 260 meshes and ships with none of them

260 of the 277 mesh files contain:

```xml
<Inline DEF='AxesDisplay' description='RGB display axes showing XYZ direction in local coordinate system'
        url='"AxesDisplay.x3d"'/>
```

`assets/loa5/meshes/AxesDisplay.x3d` does not exist, and — unlike every other `Inline`
in these files — the `url` has **no fallback list**. Every other inline offers a local
path *and* a `https://www.web3d.org/x3d/content/examples/...` mirror; this one offers a
single relative path.

Consequence: loading the full skeleton fires **260 hard 404s**. In a browser this is
260 failed requests before the scene is usable.

```
$ grep -l "AxesDisplay" assets/loa5/meshes/*.x3d | wc -l
     260
$ ls assets/loa5/meshes/AxesDisplay.x3d
ls: No such file or directory
```

**Fix:** ship `AxesDisplay.x3d`, or give the `Inline` the same web fallback the others have.

---

## 2. `l_tarsal_distal_phalanx_5.x3d` contains no geometry

The file exists (7,630 bytes) but has **zero `IndexedFaceSet` and zero `Coordinate`
nodes** — it is header, `TouchSensor` and `Transform` boilerplate wrapped around
nothing. Its right-side twin is a complete mesh.

```
                              bytes   IFS   Coordinate
l_tarsal_distal_phalanx_5.x3d  7630     0            0
r_tarsal_distal_phalanx_5.x3d 11001     2            1
```

Consequence: the left foot renders with **13 phalanges to the right foot's 14**. The
assembled skeleton has 199 bones where it should have 200, and the left little toe
visibly lacks its tip.

(There is a real anatomical fact nearby — in a substantial fraction of people the fifth
toe's middle and distal phalanges *are* fused into one segment — but that is bilateral
and symmetric. This is one-sided, so it is an asset defect, not a variant.)

**Fix:** regenerate the mesh, or mirror `r_tarsal_distal_phalanx_5.x3d`.

---

## 3. The ethmoid is modelled as two lateral halves

`assets/loa5/meshes/` contains **`ethmoid.x3d`, `l_ethmoid.x3d` and `r_ethmoid.x3d`**, and
`loa5_humanoid.x3dfrag` inlines the two halves rather than the single bone.

The ethmoid is one unpaired midline bone of the neurocranium. Splitting it into `l_`/`r_`
makes the assembled cranium count **9 bones where the canonical count is 8**, and it
means a student clicking the "ethmoid" gets one half of it.

**Fix:** inline `ethmoid.x3d`, which already exists — or, if the split is deliberate (for
per-orbit selection), document it, because it silently changes the bone count.

---

## 4. The auditory ossicles and the hyoid are absent

No `malleus`, `incus`, `stapes` or `hyoid` mesh exists in the set. That is 7 of the 206
bones of the adult skeleton (6 ossicles + hyoid).

The ossicles are arguably out of scope for a surface skeleton — they live inside the
temporal bone. The **hyoid is not**: it is a visible, palpable, freestanding bone of the
neck, it is anatomically notable precisely *because* it articulates with no other bone,
and its absence is conspicuous in any scene that shows the mandible and cervical spine.

**Fix:** add `hyoid.x3d`. Consider documenting the ossicles as a deliberate omission.

---

## 5. `normalize_loa5_meshes.py` silently whitens the teeth

Not an asset bug but a trap for anyone processing this set. The regex

```python
re.sub(r"<Material\b[^>]*/>", ...)          # normalize_loa5_meshes.py
```

also matches `<Material USE='ToothMaterial'/>`. Rewriting a `USE` reference as a
definition severs it from its `DEF`, and all 32 teeth (which share one `ToothMaterial`
via `USE`) lose their material and render pure white.

34 meshes still carry legacy Phong `<Material>` (the 32 `tooth_*` plus `l_/r_ethmoid`).
Converting them to `PhysicalMaterial` is worth doing — they blow out under PBR studio
lighting — but the conversion must **retag `USE` references without touching their
attributes**, never rewrite them as definitions. See `flatten_anatomy.py:phong_to_physical`.

---

## Reproducing the counts

```
$ .venv/bin/python flatten_anatomy.py assets/loa5/loa5_humanoid.x3dfrag build_anatomy/skeleton.x3dfrag
{"inlined": 260, "bones_addressable": 257, "def_collisions": {}, ...}

# 257 parts = 199 bones + 32 teeth + 23 discs + 3 cartilage
# 199 bones vs the canonical 206:
#   +1  cranium            (ethmoid split l_/r_)
#   -6  auditory ossicles  (not modelled)
#   -1  hyoid              (not modelled)
#   -1  foot phalanges     (l_tarsal_distal_phalanx_5 is empty)
#   ---
#   -7  net
```

## A note in the other direction

These files are *better* than they are given credit for. Every one of the 257 leaf meshes
already carries a `TouchSensor`, a DEF'd material, a hidden close-up `Viewpoint`, and real
anatomical prose in `<meta name='description'>` — 275 of 277 have a description written by
hand. The interactivity for an anatomy explorer was authored into these assets years ago
and simply never surfaced, because `Inline` puts each mesh in its own DEF namespace and
nothing downstream reached across that boundary.

The explorer this report came out of does reach across it. The craft was already there.
