#!/usr/bin/env python3
"""Flatten the canonical LOA5 HAnim skeleton into one addressable scene graph.

The Web3D bone meshes (assets/loa5/meshes/*.x3d) already carry everything an
anatomy explorer needs -- a TouchSensor, a named material, and real anatomical
prose in <meta name='description'> -- but they are pulled in via <Inline>, and
X3D gives each Inline its own DEF namespace. From the host page you cannot
recolor a bone that lives behind an Inline boundary.

(X3D's IMPORT/EXPORT *does* bridge that boundary -- verified against X_ITE
11.6.6 via scene.getImportedNode() -- but it keeps 260 sub-documents alive, and
with them the per-mesh boilerplate: every mesh ships its own DirectionalLight,
Viewpoint and BooleanToggle. Inlining all of them puts 260 stray lights in the
scene, which makes deliberate studio lighting impossible. So: flatten, prune.)

This resolves every Inline into a single namespace and gives each BONE -- not
each segment, and not each file; the teeth and the ethmoid each need their own rule -- the naming triple the UI drives:

    <bone>        the Transform            -> hide / show   (region toggles)
    TS_<bone>     the TouchSensor          -> isOver / touchTime  (picking)
    MAT_<bone>    the PhysicalMaterial     -> baseColor      (gold highlight)

and writes bone_manifest.json (name, display name, anatomical prose, region) as
the label corpus for the overlay.

    ./flatten_anatomy.py assets/loa5/loa5_humanoid.x3dfrag out/skeleton.x3d
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

from lxml import etree

MESHDIR = "assets/loa5/meshes"

# Structure we keep when splicing a mesh document into the parent.
RENDERABLE = {"Transform", "Group", "Shape", "Switch", "Collision", "LOD", "Inline"}

# Per-mesh boilerplate. Every bone file ships a hidden close-up Viewpoint, a
# blue DirectionalLight, a BooleanToggle and the ROUTEs binding them to its own
# TouchSensor -- a self-contained "click me" demo that made sense when the bone
# was viewed alone. Multiplied by 260 it is 260 lights and 260 viewpoints in the
# bind stack. We drive selection from the host page instead, so all of it goes.
BOILER_TAG = {"BooleanToggle", "ROUTE", "Viewpoint", "ViewpointGroup",
              "NavigationInfo", "Background", "DirectionalLight", "WorldInfo",
              "TouchSensor"}
BOILER_DEF = {"UserTouchState", "HiddenViewpoint", "HiddenLight",
              "CenterOfRotationForJoint"}  # the last one wraps the AxesDisplay Inline

# The canonical humanoid also carries 13 debug boxes at joint centers (the
# yellow/red cubes stuck to the elbows and knees in the existing renders). They
# mark 13 of 150 joints -- an arbitrary subset that just reads as debris.
BOILER_DEF_PREFIX = ("YellowBoxAtJointCenter", "RedBoxAtJointCenter")

# The three material DEFs the corpus actually uses (audited across all 277).
MATERIAL_DEFS = {"BoneMaterial", "ToothMaterial", "CartilageMaterial"}

# --- anatomy ---------------------------------------------------------------
# Axial skeleton: skull, ossicles, hyoid, vertebral column, ribs, sternum.
# Appendicular: the limbs and the girdles that hang them off the axial skeleton.
AXIAL_EXACT = {
    "skull", "cranium", "frontal", "occipital", "sphenoid", "ethmoid", "vomer",
    "mandible", "jaw", "hyoid", "sternum", "sacrum", "sacrum_bone", "coccyx",
    "upperTeeth", "lowerTeeth", "manubrium", "xiphoid_process",
}
AXIAL_PREFIX = (
    "c1", "c2", "c3", "c4", "c5", "c6", "c7",          # cervical (+ their discs)
    "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11", "t12",
    "l1", "l2", "l3", "l4", "l5",                      # lumbar
    "tooth_", "skull_",
)
AXIAL_SUBSTR = (
    "rib", "vertebra", "parietal", "temporal", "nasal", "lacrimal", "palatine",
    "zygomatic", "maxilla", "conchae", "costal_cartilage", "incus", "malleus",
    "stapes", "disc",
)


def region_of(bone: str) -> str:
    """axial | appendicular -- drives the region toggle in the overlay."""
    b = bone.lower()
    core = re.sub(r"^[lr]_", "", b)
    if core in AXIAL_EXACT or b in AXIAL_EXACT:
        return "axial"
    # careful: "l5" is a lumbar vertebra, but "l_..." is a left-side limb bone.
    if re.match(r"^[ctl]\d+(disc)?$", core):
        return "axial"
    if core.startswith(AXIAL_PREFIX):
        return "axial"
    if any(s in core for s in AXIAL_SUBSTR):
        return "axial"
    return "appendicular"


# --- what each part actually IS -------------------------------------------
# The model has 256 clickable parts but a human skeleton is canonically 206
# bones. The difference is not an error: the model also carries teeth, the
# intervertebral discs and some cartilage, none of which are bones. Classifying
# every part here means the explorer's "why 256, not 206?" panel is grounded in
# counts measured from the actual model, not asserted.
def kind_of(bone: str) -> str:
    b = bone.lower()
    if b.startswith("tooth_"):
        return "tooth"
    if b.endswith("disc"):
        return "disc"
    if "cartilage" in b or b == "pubic_symphysis":
        return "cartilage"
    return "bone"


GROUPS = [
    (r"^tooth_",                                   "Teeth"),
    (r"^[ctl]\d+disc$",                            "Intervertebral discs"),
    (r"^c[1-7]$",                                  "Cervical vertebrae"),
    (r"^t\d+$",                                    "Thoracic vertebrae"),
    (r"^l[1-5]$",                                  "Lumbar vertebrae"),
    (r"^(sacrum_bone|coccyx)$",                    "Sacrum & coccyx"),
    (r"rib\d+$",                                   "Ribs"),
    (r"^sternum$",                                 "Sternum"),
    (r"costal_cartilage$",                         "Costal cartilage"),
    (r"^hyoid$",                                   "Hyoid"),
    (r"^(frontal|occipital|sphenoid)$",            "Cranium"),
    (r"(parietal|temporal|ethmoid)$",              "Cranium"),
    (r"^(mandible|vomer)$",                        "Facial skeleton"),
    (r"(maxilla|zygomatic|nasal|lacrimal|palatine|conchae)$", "Facial skeleton"),
    (r"(clavicle|scapula)$",                       "Shoulder girdle"),
    (r"(humerus|radius|ulna)$",                    "Arm"),
    (r"(scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate)$", "Carpals"),
    (r"^[lr]_metacarpal_\d$",                      "Metacarpals"),
    (r"^[lr]_carpal_.*phalanx",                    "Hand phalanges"),
    (r"(hip_bone|pubic_symphysis)$",               "Pelvic girdle"),
    (r"(femur|patella|tibia|fibula)$",             "Leg"),
    (r"(calcaneus|talus|navicular|cuboid|cuneiform_\d)$", "Tarsals"),
    (r"^[lr]_metatarsal_\d$",                      "Metatarsals"),
    (r"^[lr]_tarsal_.*phalanx",                    "Foot phalanges"),
]


def group_of(bone: str) -> str:
    for pat, name in GROUPS:
        if re.search(pat, bone):
            return name
    return "Other"


def display_name(bone: str) -> str:
    """l_scaphoid -> 'L. Scaphoid';  c4 -> 'C4';  tooth_canine_11_23 -> ..."""
    b = bone
    side = ""
    if b.startswith("l_"):
        side, b = "L. ", b[2:]
    elif b.startswith("r_"):
        side, b = "R. ", b[2:]
    if re.fullmatch(r"[ctl]\d+", b):
        return side + b.upper()
    if re.fullmatch(r"[ctl]\d+disc", b):
        return side + b[:-4].upper() + " Disc"
    return side + b.replace("_", " ").title()


def find_local(url_token: str) -> str | None:
    for p in (url_token, os.path.join(MESHDIR, os.path.basename(url_token))):
        if os.path.exists(p):
            return p
    return None


def prune(el: etree._Element) -> None:
    """Strip the per-mesh interactive boilerplate, in place."""
    for ch in list(el):
        if not isinstance(ch.tag, str):          # comments / PIs
            el.remove(ch)
            continue
        d = ch.get("DEF") or ""
        if ch.tag in BOILER_TAG or d in BOILER_DEF or d.startswith(BOILER_DEF_PREFIX):
            el.remove(ch)
            continue
        prune(ch)


def phong_to_physical(el: etree._Element) -> int:
    """The 32 teeth + the ethmoids still carry legacy Phong <Material>.

    Under studio PBR lighting they blow out. Convert them in memory.

    Two traps here, both of which silently whiten the teeth:

    1. The repo's normalize_loa5_meshes.py uses `<Material\\b[^>]*/>`, which also
       matches `<Material USE='ToothMaterial'/>` and rewrites it into a
       definition -- severing the USE link. Never rewrite a USE as a definition.
    2. But you cannot leave the USE alone either: a `<Material USE='X'/>` whose
       DEF has become a PhysicalMaterial is a node-type mismatch. USE must agree
       with the type of its DEF. So retag the references too -- attributes
       untouched, since a USE node carries none.
    """
    n = 0
    for m in list(el.iter("Material")):
        if m.get("USE"):                      # a reference: retag only (trap 2)
            m.tag = "PhysicalMaterial"
            continue
        diffuse = m.get("diffuseColor", "0.8 0.8 0.8")
        m.tag = "PhysicalMaterial"
        m.set("baseColor", diffuse)
        m.set("metallic", "0")
        m.set("roughness", "0.55")
        for dead in ("diffuseColor", "ambientIntensity", "specularColor",
                     "shininess", "emissiveColor"):
            m.attrib.pop(dead, None)
        n += 1
    return n


def harvest_meta(path: str) -> tuple[str, str]:
    """(anatomical prose, the mesh's own TouchSensor description)"""
    x = open(path, encoding="utf-8", errors="replace").read()
    d = re.search(r"<meta content='([^']*)' name='description'/>", x)
    t = re.search(r"<TouchSensor DEF='UserTouchSensor' description='([^']*)'", x)
    return (d.group(1) if d else ""), (t.group(1) if t else "")


def split_bones() -> dict[str, str]:
    """child mesh -> parent mesh, for ONE bone stored across several files.

    Most geometry-free mesh files are LOA-1 *regions* -- `skull.x3d` inlines the
    22 skull bones, `l_carpal.x3d` inlines 4 carpals -- and their children really
    are separate bones, so each child is its own clickable part.

    `ethmoid.x3d` is not like that. It has no geometry of its own and inlines
    `l_ethmoid.x3d` + `r_ethmoid.x3d`: the two labyrinths of a SINGLE unpaired
    midline bone. Keying identity per file would count the ethmoid twice and
    hand the user half a bone when they click it -- the cranium would come to 9
    where the canonical count is 8.

    The test that separates the two cases: a container is a split BONE (not a
    region) when every child's name reduces to the container's own name once the
    l_/r_ side prefix is stripped. Computed, so a future split is caught too.
    """
    out: dict[str, str] = {}
    for path in glob.glob(os.path.join(MESHDIR, "*.x3d")):
        parent = os.path.basename(path)[:-4]
        x = open(path, encoding="utf-8", errors="replace").read()
        if any(re.search("<" + g, x) for g in
               ("IndexedFaceSet", "IndexedTriangleSet", "TriangleSet")):
            continue                                     # has its own geometry
        kids = []
        for m in re.finditer(r"<Inline[^>]*\burl='([^']*)'", x):
            toks = re.findall(r'"([^"]+)"', m.group(1))
            if toks and not toks[0].startswith("http") and "AxesDisplay" not in toks[0]:
                kids.append(os.path.basename(toks[0])[:-4])
        base = lambda n: re.sub(r"^[lr]_", "", n)
        if kids and all(base(k) == base(parent) for k in kids):
            for k in kids:
                out[k] = parent
    return out


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    outdir = os.path.dirname(os.path.abspath(dst))
    os.makedirs(outdir, exist_ok=True)

    # The frag is a bare HAnimHumanoid, not a whole X3D document.
    frag = open(src, encoding="utf-8").read()
    root = etree.fromstring(
        f"<Scene>{frag}</Scene>".encode(),
        etree.XMLParser(remove_comments=True, huge_tree=True),
    )

    # The joint-center debug boxes sit in the humanoid frag itself, not inside
    # any mesh, so the per-mesh prune() never sees them. Strip them here.
    markers = 0
    for tr in list(root.iter("Transform")):
        if (tr.get("DEF") or "").startswith(BOILER_DEF_PREFIX):
            tr.getparent().remove(tr)
            markers += 1

    GEOM = ("IndexedFaceSet", "IndexedTriangleSet", "TriangleSet",
            "IndexedTriangleStripSet")
    bones: list[dict] = []
    phong = 0
    inlined = dropped = 0
    seen: set[str] = set()

    # Resolve Inlines to fixpoint (skull/jaw/teeth inline further bone files).
    #
    # Identity comes from the FILE, not from any DEF inside it. The tooth files
    # name their Transforms 'lcaninec'/'lcaniner' rather than after the file, so
    # keying on an inner DEF would drop all 32 of them on the floor -- and leave
    # 32 colliding ToothMaterial DEFs behind. Each mesh's kept content is wrapped
    # in one identity Transform DEF=<bone>, which is the unit the UI addresses.
    changed = True
    while changed:
        changed = False
        for inl in list(root.iter("Inline")):
            urls = re.findall(r'"([^"]+)"', inl.get("url", "")) or [inl.get("url", "")]
            path = next((find_local(u) for u in urls
                         if u.endswith(".x3d") and not u.startswith("http") and find_local(u)),
                        None)
            par = inl.getparent()
            idx = par.index(inl)
            if path is None:
                # AxesDisplay.x3d: referenced by 260 meshes, ships with none of
                # them, and has no web fallback -- a hard 404 per bone. Drop it.
                par.remove(inl)
                dropped += 1
                changed = True
                continue

            bone = os.path.basename(path)[:-4]
            sub = etree.parse(path, etree.XMLParser(remove_comments=True,
                                                    huge_tree=True)).getroot().find("Scene")
            keep = [c for c in sub if isinstance(c.tag, str) and c.tag in RENDERABLE]

            for ch in keep:
                prune(ch)

            # Most meshes are a single <Transform DEF='l_femur'> -- adopt it as
            # the bone rather than nesting a second Transform with the same DEF
            # (that would duplicate every bone's DEF). The teeth files, whose
            # Transforms are named 'lcaninec'/'lcaniner', do get a wrapper.
            if len(keep) == 1 and keep[0].tag == "Transform" and keep[0].get("DEF") == bone:
                wrap = keep[0]
            else:
                wrap = etree.Element("Transform")
                for ch in keep:
                    wrap.append(ch)

            # Tag which FILE this subtree came from and move on. Identity cannot
            # be decided here: a container's geometry only exists once its own
            # children have been inlined, which happens on a later pass.
            wrap.set("_src", bone)
            wrap.set("_path", path)

            par.insert(idx, wrap)
            par.remove(inl)
            inlined += 1
            changed = True

    # --- second pass: decide what is a bone ---------------------------------
    # Bottom-up, because the rule is about what a subtree CONTAINS:
    #
    #   a tagged subtree becomes a clickable bone iff it has geometry, is not a
    #   piece of a split bone, and contains no tagged subtree that is already a
    #   bone.
    #
    # That last clause is what keeps `skull.x3d` from becoming one giant "bone":
    # it contains 22 subtrees that each claim identity, so it claims none. And it
    # is what lets `ethmoid.x3d` claim identity: its two children are pieces of
    # itself, they claim nothing, so the container is the bone.
    MERGED = split_bones()

    def claim(el: etree._Element) -> bool:
        claimed_below = False
        for ch in el:
            claimed_below |= claim(ch)

        src = el.get("_src")
        if src is None:
            return claimed_below
        path = el.get("_path")
        del el.attrib["_src"], el.attrib["_path"]

        if src in MERGED or claimed_below:
            return claimed_below
        if not any(True for g in GEOM for _ in el.iter(g)):
            return False
        if src in seen:
            return False
        seen.add(src)

        nonlocal phong
        # `ethmoid.x3d` keeps an empty positioning <Transform DEF='ethmoid'>
        # beside its two Inlines, so the wrapper we build for the file collides
        # with it. The inner one carries nothing we need; drop its name.
        for d in el.iter():
            if d is not el and d.get("DEF") == src:
                del d.attrib["DEF"]
        el.set("DEF", src)
        phong += phong_to_physical(el)

        # One material per bone, so one JS write highlights the whole thing.
        # The ethmoid arrives as two halves, each carrying its own DEF'd
        # BoneMaterial -- leave both and they collide, and only half the bone
        # would light up. Collapse every later definition into a USE of the first.
        renamed: dict[str, str] = {}
        canonical: str | None = None
        for m in list(el.iter("PhysicalMaterial")):
            if m.get("USE"):
                continue
            old = m.get("DEF")
            if canonical is None:
                canonical = f"MAT_{src}"
                m.set("DEF", canonical)
                if old:
                    renamed[old] = canonical
            elif old in MATERIAL_DEFS or old is None:
                if old:
                    renamed[old] = canonical
                for a in list(m.attrib):
                    del m.attrib[a]
                m.set("USE", canonical)
        for m in el.iter("PhysicalMaterial"):
            u = m.get("USE")
            if u and u in renamed:
                m.set("USE", renamed[u])

        # sensor as a sibling of this bone's geometry.
        # description='' on purpose: X_ITE renders TouchSensor.description as a
        # native tooltip, which would fight the HTML label overlay.
        ts = etree.Element("TouchSensor")
        ts.set("DEF", f"TS_{src}")
        ts.set("description", "")
        el.insert(0, ts)

        desc, touch = harvest_meta(path)
        bones.append({
            "name": src,
            "display": display_name(src),
            "region": region_of(src),
            "kind": kind_of(src),
            "groupFallback": group_of(src),
            "description": desc or touch,
        })
        return True

    claim(root)

    # --- integrity: DEF collisions and coordIndex bounds -------------------
    defs = collections.Counter(e.get("DEF") for e in root.iter() if e.get("DEF"))
    collisions = {k: v for k, v in defs.items() if v > 1}

    bad_index = []
    for ifs in root.iter("IndexedFaceSet"):
        coord = next((c for c in ifs.iter("Coordinate")), None)
        if coord is None or not coord.get("point"):
            continue
        npts = len(coord.get("point").split()) // 3
        idx = [int(i) for i in ifs.get("coordIndex", "").split() if i.lstrip("-").isdigit()]
        if idx and max(idx) >= npts:
            bad_index.append((ifs.get("DEF"), max(idx), npts))

    # --- emit --------------------------------------------------------------
    humanoid = root.find("HAnimHumanoid")
    etree.ElementTree(humanoid).write(dst, encoding="UTF-8", xml_declaration=False,
                                      pretty_print=False)

    bones.sort(key=lambda b: (b["region"], b["name"]))
    kinds = collections.Counter(b["kind"] for b in bones)
    groups = collections.Counter(b["groupFallback"] for b in bones)
    manifest = {
        "bones": bones,
        "counts": {
            "total": len(bones),
            "axial": sum(b["region"] == "axial" for b in bones),
            "appendicular": sum(b["region"] == "appendicular" for b in bones),
            "with_prose": sum(bool(b["description"]) for b in bones),
        },
        # measured, not asserted: the raw material for the "why N, not 206?" panel
        "kinds": dict(kinds),
        "groups": dict(sorted(groups.items(), key=lambda kv: -kv[1])),
    }
    mpath = os.path.join(outdir, "bone_manifest.json")
    json.dump(manifest, open(mpath, "w"), indent=1)

    print(json.dumps({
        "inlined": inlined,
        "dropped_AxesDisplay": dropped,
        "dropped_debug_boxes": markers,
        "bones_addressable": len(bones),
        "phong_converted": phong,
        "def_collisions": collisions,
        "coordIndex_out_of_range": bad_index,
        "MB": round(os.path.getsize(dst) / 1e6, 2),
        **manifest["counts"],
    }, indent=1))


if __name__ == "__main__":
    main()
