#!/usr/bin/env python3
"""
Normalize the Web3D Medical bone assets for PBR use in the classroom scene.

For each inlined regional bone file in assets/medical/ (not BonesAllSkeleton,
which is kept as a pristine v3.3 reference):
  - upgrade X3D 3.3 Interchange  ->  X3D 4.0 Immersive (DOCTYPE + X3D header)
  - convert every classic <Material> to <PhysicalMaterial> (metallic-roughness):
        diffuseColor -> baseColor, emissiveColor/transparency preserved,
        bone is dielectric so metallic=0, roughness=0.72 (matte bone)

Re-runnable: PhysicalMaterial elements are left untouched on a second pass.
"""
import glob
import re

INLINED = [
    "BonesHead", "BonesMandible", "BonesTeethTop", "BonesTeethBottom",
    "BonesSpine", "BonesChest", "BonesGirdle",
    "BonesLeftHumerus", "BonesLeftRadiusUlna", "BonesLeftHand",
    "BonesRightHumerus", "BonesRightRadiusUlna", "BonesRightHand",
    "BonesLeftFemur", "BonesLeftTibiaFibula", "BonesLeftFoot",
    "BonesRightFemur", "BonesRightTibiaFibula", "BonesRightFoot",
]

METALLIC = "0"
ROUGHNESS = "0.72"

def attr(text, name):
    m = re.search(rf"{name}='([^']*)'", text)
    return m.group(1) if m else None

def to_physical(m):
    body = m.group(0)
    base = attr(body, "diffuseColor") or "1 1 1"
    parts = [f"baseColor='{base}'", f"metallic='{METALLIC}'", f"roughness='{ROUGHNESS}'"]
    emis = attr(body, "emissiveColor")
    if emis and emis.strip() not in ("0 0 0", "0.0 0.0 0.0"):
        parts.append(f"emissiveColor='{emis}'")
    trans = attr(body, "transparency")
    if trans and float(trans) > 0:
        parts.append(f"transparency='{trans}'")
    return "<PhysicalMaterial " + " ".join(parts) + "/>"

def process(path):
    src = open(path).read()
    orig = src
    src = src.replace('"ISO//Web3D//DTD X3D 3.3//EN" "https://www.web3d.org/specifications/x3d-3.3.dtd"',
                      '"ISO//Web3D//DTD X3D 4.0//EN" "https://www.web3d.org/specifications/x3d-4.0.dtd"')
    src = src.replace("profile='Interchange' version='3.3'", "profile='Immersive' version='4.0'")
    src = src.replace("x3d-3.3.xsd", "x3d-4.0.xsd")
    n = len(re.findall(r"<Material\b[^>]*/>", src))
    src = re.sub(r"<Material\b[^>]*/>", to_physical, src)
    if src != orig:
        open(path, "w").write(src)
    return n

if __name__ == "__main__":
    total = 0
    for name in INLINED:
        p = f"assets/medical/{name}.x3d"
        c = process(p)
        total += c
        print(f"  {name:26s} {c:3d} materials -> PhysicalMaterial")
    print(f"converted {total} materials across {len(INLINED)} files")
