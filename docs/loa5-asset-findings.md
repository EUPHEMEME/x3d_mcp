# Findings in the HAnim `AllBonesLOA5Skeletons` bone-mesh set

Surfaced while building the [LOA5 Anatomy Explorer](../demo-releases/2026-07-12_anatomy-explorer/),
which makes all 256 parts of the LOA-5 skeleton individually pickable. Making every
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
assembled skeleton has 198 bones where it should have 199, and the left little toe
visibly lacks its tip.

(There is a real anatomical fact nearby — in a substantial fraction of people the fifth
toe's middle and distal phalanges *are* fused into one segment — but that is bilateral
and symmetric. This is one-sided, so it is an asset defect, not a variant.)

**Fix:** regenerate the mesh, or mirror `r_tarsal_distal_phalanx_5.x3d`.

---

## 3. NOT A BUG — the ethmoid. A trap for tooling, and we fell in it

Recorded because the first draft of this report got it wrong, and the mistake is one any
tool processing this set will make.

`assets/loa5/meshes/` contains `ethmoid.x3d`, `l_ethmoid.x3d` and `r_ethmoid.x3d`. The
ethmoid is one unpaired midline bone, so three files looks like a double-count — and if
you decide *what a bone is* by looking at filenames, it is one: you get a cranium of 9
where the canonical count is 8, and a user who clicks the ethmoid gets half of it.

But the assets are **correct**. `loa5_humanoid.x3dfrag` inlines `ethmoid.x3d` exactly
once, and `ethmoid.x3d` is a container with no geometry of its own that inlines the two
lateral labyrinths. The bone is assembled properly. The count is right.

The trap is that this container is structurally identical to the LOA-1 *region* containers
(`skull.x3d` inlines 22 skull bones, `l_carpal.x3d` inlines 4 carpals) — all are
geometry-free files that inline others — but it means something completely different.
A region's children are separate bones. The ethmoid's children are **pieces of one bone**.

The discriminator, if you need one: a container is a split *bone*, not a *region*, when
every child's name reduces to the container's own name once the `l_`/`r_` prefix is
stripped. `flatten_anatomy.py:split_bones()` computes it that way, so a future split is
caught automatically. Across all 277 meshes, **the ethmoid is the only case**.

**No fix needed.** Possibly worth a comment in `ethmoid.x3d` saying so.

---

## 4. The auditory ossicles and the hyoid are absent

No `malleus`, `incus`, `stapes` or `hyoid` mesh exists in the set — not under those names,
not under any other: the string "hyoid" does not appear in the contents of any of the 277
mesh files, nor anywhere in `loa5_humanoid.x3dfrag`. That is 7 of the 206 bones of the
adult skeleton (6 ossicles + hyoid).

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
{"inlined": 260, "bones_addressable": 256, "def_collisions": {}, ...}

# 256 parts = 198 bones + 32 teeth + 23 discs + 3 cartilage
# 198 bones vs the canonical 206:
#   -6  auditory ossicles  (not modelled)
#   -1  hyoid              (not modelled)
#   -1  foot phalanges     (l_tarsal_distal_phalanx_5 has no geometry)
#   ---
#   -8  net
#
# Every one of the 8 is a genuine ABSENCE from the model. There is no
# compensating over-count -- the earlier +1 for a "split ethmoid" was an artifact
# of our own flattener, not a defect in the assets. See section 3.
```

## A note in the other direction

These files are *better* than they are given credit for. Every one of the 256 leaf bones
already carries a `TouchSensor`, a DEF'd material, a hidden close-up `Viewpoint`, and real
anatomical prose in `<meta name='description'>` — 275 of 277 have a description written by
hand. The interactivity for an anatomy explorer was authored into these assets years ago
and simply never surfaced, because `Inline` puts each mesh in its own DEF namespace and
nothing downstream reached across that boundary.

The explorer this report came out of does reach across it. The craft was already there.
