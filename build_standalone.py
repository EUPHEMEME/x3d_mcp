#!/usr/bin/env python3
"""
Build a self-contained, double-clickable demo HTML.

Browsers block X_ITE from fetching a scene's .x3d, its inlined bone meshes, their
nested sub-bone Inlines, and textures over file://. This resolves EVERY Inline
recursively (downloading any missing sub-bone referenced by an http fallback URL,
caching it under assets/loa5/meshes/), drops unresolvable helper Inlines
(AxesDisplay), and embeds textures as base64 data: URIs. The fully self-contained
scene is then handed to X_ITE via a data: URL (a CORS-allowed scheme), so the
page opens by double-click with no local web server. Only the X_ITE library
loads from a CDN.

Usage: build_standalone.py scene.x3d out.html "Title"
"""
import base64
import os
import subprocess
import sys
from lxml import etree

# Keep Inline too: aggregate bones (skull, pelvis, hands) hold their real
# sub-bones as sibling Inlines; carrying them lets the loop resolve recursively.
RENDERABLE = {"Transform", "Group", "Shape", "Switch", "Collision", "LOD", "Inline"}
MESHDIR = "assets/loa5/meshes"

def candidates(url_attr):
    return [t for t in url_attr.replace('"', " ").split() if t]

def find_local(name):
    for p in (name, os.path.join(MESHDIR, os.path.basename(name))):
        if os.path.exists(p):
            return p
    return None

def ensure_downloaded(url):
    fn = os.path.join(MESHDIR, os.path.basename(url))
    if not os.path.exists(fn):
        subprocess.run(["curl", "-sL", "-o", fn, url], capture_output=True)
        if os.path.exists(fn):
            t = open(fn, errors="ignore").read()
            open(fn, "w").write("\n".join(l for l in t.splitlines()
                                          if not l.startswith("<!DOCTYPE")))
    return fn if os.path.exists(fn) and os.path.getsize(fn) > 200 else None

def resolve(cands):
    for c in cands:                                  # prefer a local .x3d
        if c.endswith(".x3d") and not c.startswith("http"):
            p = find_local(c)
            if p:
                return p
    for c in cands:                                  # else download an http .x3d
        if c.startswith("http") and c.endswith(".x3d"):
            p = ensure_downloaded(c)
            if p:
                return p
    return None

def inline_all(root):
    downloaded = dropped = inlined = 0
    changed = True
    while changed:
        changed = False
        for inl in list(root.iter("Inline")):
            path = resolve(candidates(inl.get("url", "")))
            parent = inl.getparent()
            if path:
                sub = etree.parse(path).getroot().find("Scene")
                idx = parent.index(inl)
                for ch in reversed([c for c in sub if c.tag in RENDERABLE]):
                    parent.insert(idx, ch)
                parent.remove(inl)
                inlined += 1
            else:
                parent.remove(inl)                   # AxesDisplay & friends
                dropped += 1
            changed = True
    # textures -> base64 data URIs
    tex = 0
    for it in root.iter("ImageTexture"):
        for c in candidates(it.get("url", "")):
            p = find_local(c) if not c.startswith("http") else None
            if p and os.path.exists(p):
                mime = "image/png" if p.lower().endswith(".png") else "image/jpeg"
                b64 = base64.b64encode(open(p, "rb").read()).decode()
                it.set("url", f'"data:{mime};base64,{b64}"')
                tex += 1
                break
    print(f"  inlined {inlined} meshes, dropped {dropped} helper Inlines, {tex} textures embedded")
    return root

def wrap(scene_xml, title):
    doc = '<?xml version="1.0" encoding="UTF-8"?>\n' + scene_xml
    b64 = base64.b64encode(doc.encode()).decode()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/x_ite@latest/dist/x_ite.min.js"></script>
  <style>
    html,body {{ margin:0; height:100%; background:#10131a; }}
    x3d-canvas {{ width:100vw; height:100vh; display:block; }}
  </style>
</head>
<body>
  <x3d-canvas src="data:model/x3d+xml;base64,{b64}"></x3d-canvas>
</body>
</html>
"""

if __name__ == "__main__":
    src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
    root = inline_all(etree.parse(src).getroot())
    open(out, "w").write(wrap(etree.tostring(root, encoding="unicode"), title))
    print(f"wrote {out} ({os.path.getsize(out)//1024} KB, self-contained)")
