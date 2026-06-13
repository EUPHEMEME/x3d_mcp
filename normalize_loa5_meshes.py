#!/usr/bin/env python3
"""
Look-dev pass for the rendered demo: convert the canonical AllBonesLOA5 bone
meshes from old-style Phong `Material` to metallic-roughness `PhysicalMaterial`.

The Web3D bone meshes carry `Material ambientIntensity='0.965'` -- ~96% ambient
reflectance, which floods the bones with flat fill under any ambient/IBL and
washes out all anatomical form. Re-authoring them as PBR (metallic 0, matte
roughness, no ambient flood) lets EnvironmentLight shade them properly.

This re-authors materials only; geometry (Coordinate/IndexedFaceSet) is
untouched. Re-runnable. The demo prioritizes look over canon -- the point is
that the X3D toolchain can take the standard geometry anywhere.

Target: assets/loa5/meshes/*.x3d  (shared by the runner and classroom demos)
"""
import glob
import re

ROUGHNESS = "0.6"
METALLIC = "0"

def to_physical(m):
    body = m.group(0)
    d = re.search(r"diffuseColor='([^']*)'", body)
    base = d.group(1) if d else "1 1 1"
    deff = re.search(r"DEF='([^']*)'", body)
    parts = ["<PhysicalMaterial"]
    if deff:
        parts.append(f"DEF='{deff.group(1)}'")
    parts.append(f"baseColor='{base}' metallic='{METALLIC}' roughness='{ROUGHNESS}'/>")
    return " ".join(parts)

if __name__ == "__main__":
    files = sorted(glob.glob("assets/loa5/meshes/*.x3d"))
    total = 0
    for f in files:
        src = open(f).read()
        new, n = re.subn(r"<Material\b[^>]*/>", to_physical, src)
        if n:
            open(f, "w").write(new)
            total += n
    print(f"converted {total} Material -> PhysicalMaterial across {len(files)} mesh files")
