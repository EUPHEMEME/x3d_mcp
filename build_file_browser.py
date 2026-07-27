#!/usr/bin/env python3
"""build_file_browser.py — Generate a spatial file browser.

Scans project directories on Hétu and produces an interactive 2D/3D file explorer
with multiple topology views (grid, tree, orbital, stack), rendered on canvas.

EUPHEME — A.H.Hoffman.
"""
import json, os, math
from pathlib import Path

SCAN_ROOTS = [
    ("~/E", "EUPHEME Research", "#fbcf57", "E"),
    ("~/x3d_mcp", "X3D MCP", "#5b9bd5", "X3D"),
    ("~/latex", "LaTeX Tools", "#e06c75", "LaTeX"),
    ("~/brush", "Brush (Gaussian Splatting)", "#98c379", "Brush"),
    ("~/MUSIC_DL", "Music", "#c678dd", "Music"),
]

FILE_COLORS = {
    ".py": "#e5c07b", ".html": "#e06c75", ".x3d": "#5b9bd5",
    ".tex": "#e06c75", ".pdf": "#c678dd", ".json": "#98c379",
    ".md": "#abb2bf", ".png": "#56b6c2", ".jpg": "#56b6c2",
    ".wav": "#c678dd", ".zip": "#6b6b68",
}

SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".cargo",
    ".cache", "target", ".zsh_sessions", "Library", ".Trash",
    ".claude", "build", ".github", ".zed", "baml_client",
    "bdist.macosx-26.0-arm64", "lib", ".thumbnails", ".local",
    ".npm", ".rustup", ".matplotlib", ".config",
}
SKIP_FILES = {".DS_Store", ".gitignore", ".dockerignore"}
MAX_DEPTH = 3
MAX_CHILDREN = 50


def scan_dir(root, max_depth=MAX_DEPTH, depth=0):
    root = Path(root).expanduser()
    if not root.exists():
        return None
    node = {"n": root.name, "p": str(root), "t": "d", "c": [], "e": "", "s": 0}
    if depth >= max_depth:
        return node
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return node
    count = 0
    for entry in entries:
        if entry.name in SKIP_FILES:
            continue
        if entry.is_dir():
            if entry.name in SKIP_DIRS:
                continue
            child = scan_dir(entry, max_depth, depth + 1)
            if child:
                node["c"].append(child)
                count += 1
        else:
            ext = entry.suffix.lower()
            try:
                sz = entry.stat().st_size
            except OSError:
                sz = 0
            node["c"].append({"n": entry.name, "p": str(entry), "t": "f", "e": ext, "s": sz, "c": []})
            count += 1
        if count >= MAX_CHILDREN:
            break
    return node


def count_nodes(node):
    c = 1
    for child in node.get("c", []):
        c += count_nodes(child)
    return c


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hétu — File Browser</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root { color-scheme: dark; }
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; background:#04050a; color:#e9eedc;
  font-family:'DM Mono',ui-monospace,monospace; overflow:hidden; }

#header {
  position:fixed; top:0; left:0; right:0; z-index:100;
  height:48px; background:rgba(7,10,17,0.95);
  border-bottom:1px solid #2b3550;
  display:flex; align-items:center; padding:0 16px; gap:12px;
  backdrop-filter:blur(8px);
}
#header h1 { font-size:15px; font-weight:600; }
#header h1 b { color:#fbcf57; }
#header .sub { font-size:11px; color:#73839f; }

.topo-bar { display:flex; gap:4px; margin-left:auto; }
.topo-btn {
  padding:5px 12px; border-radius:999px; border:1px solid #2b3550;
  background:transparent; color:#73839f; font:inherit; font-size:11px;
  cursor:pointer; transition:all 0.15s;
}
.topo-btn:hover { border-color:#5b9bd5; color:#e9eedc; }
.topo-btn.active { background:#fbcf57; color:#0a0c12; border-color:#fbcf57; font-weight:700; }

canvas { position:fixed; top:48px; left:0; width:100%; height:calc(100% - 48px); display:block; }

#info {
  position:fixed; bottom:16px; left:16px; z-index:50;
  background:rgba(7,10,17,0.94); border:1px solid #2b3550;
  border-radius:10px; padding:14px 18px; max-width:400px;
  font-size:12px; line-height:1.6; backdrop-filter:blur(8px);
  box-shadow:0 4px 20px rgba(0,0,0,0.5); display:none;
}
#info h3 { font-size:14px; margin-bottom:4px; }
#info .path { color:#73839f; font-size:10px; word-break:break-all; }
#info .tags { margin-top:6px; }
#info .tag {
  display:inline-block; background:rgba(255,255,255,0.06);
  padding:2px 8px; border-radius:4px; font-size:10px; margin:2px 4px 2px 0;
}
#info .act { margin-top:8px; padding-top:8px; border-top:1px solid #2b3550; }
#info a { color:#fbcf57; text-decoration:none; font-size:11px; }
#info a:hover { text-decoration:underline; }

#legend {
  position:fixed; top:60px; right:16px; z-index:50;
  background:rgba(7,10,17,0.94); border:1px solid #2b3550;
  border-radius:10px; padding:10px 14px; font-size:10px;
  backdrop-filter:blur(8px);
}
.lrow { display:flex; align-items:center; gap:6px; margin:3px 0; }
.ldot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }

#hint {
  position:fixed; bottom:16px; right:16px; z-index:50;
  font-size:10px; color:#73839f; text-align:right; line-height:1.6;
}
</style>
</head>
<body>

<div id="header">
  <h1><b>Hétu</b> File Browser</h1>
  <span class="sub" id="count"></span>
  <div class="topo-bar">
    <button class="topo-btn active" data-t="grid" onclick="topo('grid')">Grid</button>
    <button class="topo-btn" data-t="tree" onclick="topo('tree')">Tree</button>
    <button class="topo-btn" data-t="orbital" onclick="topo('orbital')">Orbital</button>
    <button class="topo-btn" data-t="stack" onclick="topo('stack')">Stack</button>
  </div>
</div>

<canvas id="c"></canvas>

<div id="legend">
  <div class="lrow"><div class="ldot" style="background:#fbcf57"></div> Folder</div>
  <div class="lrow"><div class="ldot" style="background:#e5c07b"></div> Python</div>
  <div class="lrow"><div class="ldot" style="background:#e06c75"></div> HTML / TeX</div>
  <div class="lrow"><div class="ldot" style="background:#5b9bd5"></div> X3D</div>
  <div class="lrow"><div class="ldot" style="background:#c678dd"></div> PDF / Media</div>
  <div class="lrow"><div class="ldot" style="background:#98c379"></div> Data</div>
</div>

<div id="info">
  <h3 id="in"></h3>
  <div class="path" id="ip"></div>
  <div class="tags" id="it"></div>
  <div class="act" id="ia"></div>
</div>

<div id="hint">scroll to zoom · drag to pan · click to inspect · double-click to open</div>

<script>
const DATA = /*DATA_JSON*/;
const FCOLORS = {"py":"#e5c07b","html":"#e06c75","x3d":"#5b9bd5","tex":"#e06c75",
  "pdf":"#c678dd","json":"#98c379","md":"#abb2bf","png":"#56b6c2","jpg":"#56b6c2",
  "wav":"#c678dd","zip":"#6b6b68"};

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W, H, dpr;
let nodes = [];
let cam = {x:0, y:0, z:1};
let drag = null;
let hovered = null, selected = null;

function resize() {
  dpr = window.devicePixelRatio || 1;
  W = canvas.clientWidth; H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
window.addEventListener('resize', () => { resize(); draw(); });

function flatten(tree, rootColor, rootShort, depth, parent) {
  var ext = (tree.e||'').replace('.','');
  var color = tree.t==='d' ? (depth===0 ? rootColor : '#fbcf57')
    : (FCOLORS[ext] || '#555');
  var n = {
    name:tree.n, path:tree.p, type:tree.t, ext:tree.e, size:tree.s,
    color:color, root:rootShort, rootColor:rootColor,
    depth:depth, parent:parent, kids:[],
    kidCount: tree.c ? tree.c.length : 0,
    x:W/2, y:H/2, tx:0, ty:0,
    r: tree.t==='d' ? (depth===0 ? 24 : 10 + Math.min((tree.c||[]).length,20)*0.4) : 5,
  };
  nodes.push(n);
  if (tree.c) {
    for (var i=0; i<tree.c.length; i++) {
      n.kids.push(flatten(tree.c[i], rootColor, rootShort, depth+1, n));
    }
  }
  return n;
}

function init() {
  resize();
  nodes = [];
  for (var i=0; i<DATA.length; i++) {
    var d = DATA[i];
    flatten(d[0], d[2], d[3], 0, null);
  }
  document.getElementById('count').textContent = nodes.length + ' items';
  topo('grid');
}

function descendants(n) {
  var r = [];
  for (var i=0; i<n.kids.length; i++) {
    r.push(n.kids[i]);
    r = r.concat(descendants(n.kids[i]));
  }
  return r;
}

function layoutGrid() {
  var roots = nodes.filter(function(n){return n.depth===0;});
  var cw = Math.max(180, (W-80) / roots.length);
  for (var ri=0; ri<roots.length; ri++) {
    var cx = 40 + ri*cw + cw/2;
    var root = roots[ri];
    root.tx = cx; root.ty = 60;
    var all = descendants(root);
    var pr = Math.max(1, Math.floor(cw/22));
    for (var i=0; i<all.length; i++) {
      var row = Math.floor(i/pr);
      var col = i % pr;
      all[i].tx = cx - (pr*11) + col*22 + 11;
      all[i].ty = 100 + row*22;
    }
  }
}

function layoutTree() {
  var roots = nodes.filter(function(n){return n.depth===0;});
  var tw = W - 100;
  var pw = tw / roots.length;
  for (var ri=0; ri<roots.length; ri++) {
    var root = roots[ri];
    var bx = 50 + ri*pw;
    layoutBranch(root, bx, bx+pw, 50);
  }
}

function layoutBranch(node, left, right, y) {
  node.tx = (left+right)/2;
  node.ty = y;
  if (node.kids.length === 0) return;
  var cw = (right-left) / node.kids.length;
  for (var i=0; i<node.kids.length; i++) {
    layoutBranch(node.kids[i], left+i*cw, left+(i+1)*cw, y+44);
  }
}

function layoutOrbital() {
  var roots = nodes.filter(function(n){return n.depth===0;});
  var cx = W/2, cy = H/2;
  for (var ri=0; ri<roots.length; ri++) {
    var a = (ri/roots.length)*Math.PI*2 - Math.PI/2;
    var R = Math.min(W,H)*0.22;
    var root = roots[ri];
    root.tx = cx + Math.cos(a)*R;
    root.ty = cy + Math.sin(a)*R;
    for (var ci=0; ci<root.kids.length; ci++) {
      var ca = a + (ci - root.kids.length/2)*0.15;
      var cr = R + 55 + root.kids[ci].depth*20;
      root.kids[ci].tx = cx + Math.cos(ca)*cr;
      root.kids[ci].ty = cy + Math.sin(ca)*cr;
      var child = root.kids[ci];
      for (var gi=0; gi<child.kids.length; gi++) {
        var ga = ca + (gi - child.kids.length/2)*0.06;
        var gr = cr + 35;
        child.kids[gi].tx = cx + Math.cos(ga)*gr;
        child.kids[gi].ty = cy + Math.sin(ga)*gr;
        var gc = child.kids[gi];
        var gd = descendants(gc);
        for (var di=0; di<gd.length; di++) {
          var da = ga + (di-2)*0.03;
          var dr = gr + 20 + di*6;
          gd[di].tx = cx + Math.cos(da)*dr;
          gd[di].ty = cy + Math.sin(da)*dr;
        }
      }
    }
  }
}

function layoutStack() {
  var roots = nodes.filter(function(n){return n.depth===0;});
  var cw = 260, gap = 20, margin = 30;
  for (var ri=0; ri<roots.length; ri++) {
    var cx = margin + ri*(cw+gap) + cw/2;
    var root = roots[ri];
    root.tx = cx; root.ty = 50;
    var yy = 85;
    for (var ci=0; ci<root.kids.length; ci++) {
      root.kids[ci].tx = cx; root.kids[ci].ty = yy; yy += 20;
      var child = root.kids[ci];
      for (var gi=0; gi<child.kids.length; gi++) {
        child.kids[gi].tx = cx+16; child.kids[gi].ty = yy; yy += 16;
        var gd = descendants(child.kids[gi]);
        for (var di=0; di<gd.length; di++) {
          gd[di].tx = cx+32; gd[di].ty = yy; yy += 13;
        }
      }
      yy += 6;
    }
  }
}

function topo(name) {
  document.querySelectorAll('.topo-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.t===name);
  });
  switch(name) {
    case 'grid': layoutGrid(); break;
    case 'tree': layoutTree(); break;
    case 'orbital': layoutOrbital(); break;
    case 'stack': layoutStack(); break;
  }
  animateTo();
}

var animId = 0;
function animateTo() {
  cancelAnimationFrame(animId);
  var done = false;
  function step() {
    done = true;
    for (var i=0; i<nodes.length; i++) {
      var n = nodes[i];
      var dx = n.tx - n.x, dy = n.ty - n.y;
      if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
        n.x += dx * 0.12;
        n.y += dy * 0.12;
        done = false;
      } else {
        n.x = n.tx; n.y = n.ty;
      }
    }
    draw();
    if (!done) animId = requestAnimationFrame(step);
  }
  step();
}

function draw() {
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(W/2 - cam.x*cam.z, H/2 - cam.y*cam.z);
  ctx.scale(cam.z, cam.z);

  // edges
  for (var i=0; i<nodes.length; i++) {
    var n = nodes[i];
    if (n.parent) {
      ctx.strokeStyle = n.rootColor + '15';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(n.parent.x, n.parent.y);
      ctx.lineTo(n.x, n.y);
      ctx.stroke();
    }
  }

  // nodes
  for (var i=0; i<nodes.length; i++) {
    var n = nodes[i];
    var isH = n===hovered, isS = n===selected;

    ctx.fillStyle = n.color;
    ctx.globalAlpha = n.depth > 2 ? 0.6 : 1;
    ctx.beginPath();
    if (n.type === 'd') {
      var s = n.r;
      ctx.moveTo(n.x, n.y - s*0.65);
      ctx.lineTo(n.x + s*0.7, n.y + s*0.35);
      ctx.lineTo(n.x - s*0.7, n.y + s*0.35);
      ctx.closePath();
    } else {
      ctx.arc(n.x, n.y, n.r, 0, Math.PI*2);
    }
    ctx.fill();

    if (isH || isS) {
      ctx.strokeStyle = isS ? '#fff' : '#aaa';
      ctx.lineWidth = isS ? 2 : 1;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // labels for roots and hovered
    if (n.depth === 0 || isH || isS) {
      ctx.fillStyle = n.depth===0 ? '#e9eedc' : '#bbb';
      ctx.font = (n.depth===0 ? 'bold 11px' : '10px') + " 'DM Mono',monospace";
      ctx.textAlign = 'center';
      var label = n.depth===0 ? n.root : n.name;
      if (label.length > 30) label = label.substring(0,28) + '..';
      ctx.fillText(label, n.x, n.y + n.r + (n.depth===0 ? 18 : 14));
    }
  }

  ctx.restore();
}

// interaction
function s2w(sx,sy) {
  return { x: (sx - W/2)/cam.z + cam.x, y: (sy - H/2)/cam.z + cam.y };
}

function hit(sx,sy) {
  var p = s2w(sx,sy);
  for (var i=nodes.length-1; i>=0; i--) {
    var n = nodes[i];
    var dx = p.x-n.x, dy = p.y-n.y;
    var hr = Math.max(n.r, 8);
    if (dx*dx+dy*dy < hr*hr) return n;
  }
  return null;
}

canvas.addEventListener('mousemove', function(e) {
  var r = canvas.getBoundingClientRect();
  var mx = e.clientX-r.left, my = e.clientY-r.top;
  if (drag) {
    cam.x = drag.cx - (e.clientX-drag.sx)/cam.z;
    cam.y = drag.cy - (e.clientY-drag.sy)/cam.z;
    draw(); return;
  }
  var h = hit(mx,my);
  if (h !== hovered) { hovered = h; canvas.style.cursor = h?'pointer':'grab'; draw(); }
});

canvas.addEventListener('mousedown', function(e) {
  var r = canvas.getBoundingClientRect();
  if (!hit(e.clientX-r.left, e.clientY-r.top)) {
    drag = {sx:e.clientX, sy:e.clientY, cx:cam.x, cy:cam.y};
    canvas.style.cursor = 'grabbing';
  }
});

canvas.addEventListener('mouseup', function(e) {
  if (drag) {
    var d = Math.abs(e.clientX-drag.sx)+Math.abs(e.clientY-drag.sy);
    drag = null;
    canvas.style.cursor = hovered?'pointer':'grab';
    if (d < 4) { sel(null); draw(); }
    return;
  }
  var r = canvas.getBoundingClientRect();
  sel(hit(e.clientX-r.left, e.clientY-r.top));
});

canvas.addEventListener('wheel', function(e) {
  e.preventDefault();
  cam.z *= e.deltaY > 0 ? 0.92 : 1.08;
  cam.z = Math.max(0.08, Math.min(6, cam.z));
  draw();
}, {passive:false});

canvas.addEventListener('dblclick', function(e) {
  var r = canvas.getBoundingClientRect();
  var n = hit(e.clientX-r.left, e.clientY-r.top);
  if (n && n.path) {
    var ext = (n.ext||'').replace('.','');
    if (['html','pdf','png','jpg'].indexOf(ext)>=0) {
      window.open('file://'+n.path, '_blank');
    }
  }
});

function sel(n) {
  selected = n;
  var panel = document.getElementById('info');
  if (!n) { panel.style.display='none'; draw(); return; }
  panel.style.display = 'block';
  var h3 = document.getElementById('in');
  h3.textContent = n.name;
  h3.style.color = n.color;
  document.getElementById('ip').textContent = n.path;

  var tags = '';
  if (n.type==='d') tags += '<span class="tag">'+n.kidCount+' items</span>';
  if (n.size > 0) {
    var sz = n.size > 1048576 ? (n.size/1048576).toFixed(1)+'MB' : (n.size/1024).toFixed(1)+'KB';
    tags += '<span class="tag">'+sz+'</span>';
  }
  tags += '<span class="tag">'+(n.ext||'folder')+'</span>';
  tags += '<span class="tag" style="color:'+n.rootColor+'">'+n.root+'</span>';
  document.getElementById('it').innerHTML = tags;

  var act = '';
  if (n.path) {
    var ext = (n.ext||'').replace('.','');
    if (['html','pdf','png','jpg'].indexOf(ext)>=0) {
      act = '<a href="file://'+n.path+'" target="_blank">Open in browser</a>';
    } else {
      act = '<a href="#" onclick="navigator.clipboard.writeText(\''+n.path.replace(/'/g,"\\'")+'\');this.textContent=\'Copied!\';return false;">Copy path</a>';
    }
  }
  document.getElementById('ia').innerHTML = act;
  draw();
}

init();
</script>
</body>
</html>"""


def main():
    results = []
    total = 0
    for root_path, label, color, short in SCAN_ROOTS:
        tree = scan_dir(root_path)
        if tree:
            n = count_nodes(tree)
            total += n
            results.append([tree, label, color, short])
            print(f"  {short}: {n} nodes")

    print(f"Total: {total} nodes across {len(results)} roots")

    data_json = json.dumps(results, separators=(',', ':'))
    html = TEMPLATE.replace('/*DATA_JSON*/', data_json)

    out = Path(__file__).parent / "file_browser.html"
    out.write_text(html)
    print(f"Written to {out} ({len(html)//1024}KB)")
    print(f"Serve with: python3 -m http.server 8099")
    print(f"Open: http://127.0.0.1:8099/file_browser.html")


if __name__ == "__main__":
    main()
