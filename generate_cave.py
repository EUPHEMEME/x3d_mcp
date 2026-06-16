#!/usr/bin/env python3
"""Potter Creek Cave -- a to-scale procedural X3D model.

Built from the measurements in William J. Sinclair, "The Exploration of
Potter Creek Cave" (University of California Publications in American
Archaeology and Ethnology, Vol. 2 No. 1, April 1904), the excavation
directed by John C. Merriam at Berkeley.

Hard numbers used (all verbatim from the report, 1 X3D unit = 1 foot):
  * main chamber: 107 ft long, ~30 ft wide at widest, roof ~75 ft above
    the lowest point of the floor
  * two fan-like breccia deposits sloping from opposite ends and
    coalescing in the middle; near-vertical chimney openings above each apex
  * access by a 42 ft vertical descent (rope ladder) at the great pit
  * galleries trend NW-SE; stratigraphy of the NW fan: upper clay to
    13.5 ft, volcanic ash ~1.5 ft, cemented breccia below

Outputs:  potter_creek_cave.x3d   (X3D 4.0 XML)
          potter_creek_cave.html  (self-contained X3DOM viewer)

The cave interior is modelled as a lofted limestone shell with an
independent breccia floor (the two coalescing fans), the chimney shafts,
the 42 ft entrance pit, a 6 ft human scale figure, and a banded
stratigraphic cut exposing the cave-earth layers.
"""

import math

# ---------------------------------------------------------------------------
# PROVENANCE -- what is documented vs. what is interpretive (imaginary).
#
# DOCUMENTED (to scale, from Sinclair 1904):
#   * 107 ft chamber length, ~30 ft max width, ~75 ft roof height
#   * two breccia fans sloping from the ends and coalescing in the middle
#   * a chimney opening above each fan apex
#   * the 42 ft vertical entrance pit ("great pit")
#   * NW-fan stratigraphy (upper clay 13.5 ft, ash 1.5 ft, breccia below)
#   * NW-SE trend, ~1500 ft elevation
#
# IMAGINARY / INTERPRETIVE (plausible cave dressing, NOT from the survey):
#   * every speleothem -- stalactites, stalagmites, columns, draperies, flowstone
#   * the exact wall shape / rugosity and the rock colouration & iron staining
#   * standing-water pools and their placement
#   * breakdown blocks (fallen rock) on the floor
#   * all lighting, lanterns, and the daylight shaft down the pit
#   * the 6 ft scale figure
# Sinclair mapped the chamber, not its formations; these make it read as a
# living cave while the geometry above stays faithful to the 1904 measurements.
# ---------------------------------------------------------------------------

FT = 1.0                      # 1 unit == 1 foot
LENGTH = 107.0                # chamber length, NW->SE  (Sinclair)
ROOF   = 75.0                 # max roof height above lowest floor
WIDE   = 30.0                 # max width  -> half-width 15

# fan apexes (debris cones under the two chimneys) and the entrance pit
NW_FAN_X = 26.0
SE_FAN_X = 82.0
PIT_X    = 9.0                # great pit / 42 ft entrance near the NW end


def fnum(x):
    """Compact float formatting for X3D attribute lists."""
    return f"{x:.3f}".rstrip("0").rstrip(".")


def fmt_pts(pts):
    return " ".join(f"{fnum(x)} {fnum(y)} {fnum(z)}" for x, y, z in pts)


def fmt_idx(faces):
    return " ".join(" ".join(str(i) for i in f) + " -1" for f in faces)


def fmt_cols(cols):
    return " ".join(f"{fnum(r)} {fnum(g)} {fnum(b)}" for r, g, b in cols)


def fmt_uvs(uvs):
    return " ".join(f"{fnum(u)} {fnum(v)}" for u, v in uvs)


def hash01(*a):
    """Deterministic pseudo-random in [0,1) from float args."""
    s = sum((i + 1) * v for i, v in enumerate(a))
    f = math.sin(s * 12.9898 + 4.1) * 43758.5453
    return f - math.floor(f)


def _vn2(x, y, seed):
    """Smooth 2D value noise in [0,1] (drives geometric wall displacement)."""
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi

    def h(a, b):
        return hash01(a + seed * 0.137, b - seed * 0.091)

    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a, b = h(xi, yi), h(xi + 1, yi)
    c, d = h(xi, yi + 1), h(xi + 1, yi + 1)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x, y, seed=0.0, octaves=4):
    """Fractal sum of value noise in [0,1]."""
    s, amp, f, tot = 0.0, 0.5, 1.0, 0.0
    for o in range(octaves):
        s += amp * _vn2(x * f, y * f, seed + o)
        tot += amp
        amp *= 0.5
        f *= 2.0
    return s / tot


def rock_color(x, y, phi, base=(0.66, 0.62, 0.55)):
    """Mottled, faintly iron-stained limestone; darker in low crevices."""
    n = 0.84 + 0.26 * hash01(x * 0.7, phi * 1.3, y * 0.5)
    # warm iron staining streaks
    stain = 0.5 + 0.5 * math.sin(0.35 * x + 1.7 * phi)
    r = base[0] * n + 0.06 * stain
    g = base[1] * n + 0.03 * stain
    b = base[2] * n
    # damp slightly toward the floor line
    if phi < 0.6:
        k = 0.78 + 0.22 * (phi / 0.6)
        r, g, b = r * k, g * k, b * k
    return (round(r, 3), round(g, 3), round(b, 3))


# ---------------------------------------------------------------------------
# profiles along the chamber (functions of x in [0, LENGTH])
# ---------------------------------------------------------------------------

def t_of(x):
    return max(0.0, min(1.0, x / LENGTH))


def half_width(x):
    """Half-width of the gallery: pinched at both ends, ~15 ft mid."""
    t = t_of(x)
    return 2.5 + 12.5 * math.sin(math.pi * t) ** 0.85


def roof_y(x):
    """Roof height above datum: low at the ends, ~75 ft over the middle."""
    t = t_of(x)
    return 16.0 + (ROOF - 16.0) * math.sin(math.pi * t) ** 0.7


def floor_y(x):
    """Breccia floor: two fans peaking under the chimneys, coalescing mid."""
    g1 = math.exp(-((x - NW_FAN_X) / 17.0) ** 2)
    g2 = math.exp(-((x - SE_FAN_X) / 17.0) ** 2)
    return 3.0 + 10.0 * g1 + 9.0 * g2


# ---------------------------------------------------------------------------
# geometry builders
# ---------------------------------------------------------------------------

# Longitudinal SECTION cut: keep only the back half (z <= 0) so the chamber
# opens toward the viewer -- the iconic way the 1904 survey drew the cave, and
# the only way the interior actually lights up on screen.
PHI_MAX = math.pi / 2.0          # phi 0..pi/2 traces floor-left -> roof apex (z=0)


TEX_FT = 16.0          # one texture tile spans this many feet


def build_shell(nstations=64, arch=22):
    """Lofted limestone walls + roof (back half), with multi-octave geometric
    displacement and UVs for the PBR rock. Returns (points, faces, uvs)."""
    pts, uvs, ring = [], [], []
    for i in range(nstations):
        x = LENGTH * i / (nstations - 1)
        wz, yf, yr = half_width(x), floor_y(x), roof_y(x)
        ymid = 0.5 * (yf + yr)
        row = []
        for k in range(arch + 1):
            phi = PHI_MAX * k / arch          # 0 -> pi/2: floor-left up to roof apex (z=0)
            z = -wz * math.cos(phi)
            y = yf + (yr - yf) * math.sin(phi)
            r = 1.0 + 0.03 * math.sin(2.7 * phi + 0.5 * i)
            yy, zz = yf + (y - yf) * r, z * r
            # push each vertex along its outward direction by fractal noise so the
            # walls have real relief (silhouette), not just a normal-mapped sheen
            d = (fbm(x * 0.06, phi * 1.5, 3.0) - 0.5) * 2.0 * 1.6
            oy, oz = yy - ymid, zz
            ol = math.hypot(oy, oz) or 1.0
            yy += d * oy / ol
            zz += d * oz / ol
            row.append((x, yy, zz))
            uvs.append((x / TEX_FT, yy / TEX_FT))
        ring.append([len(pts) + j for j in range(len(row))])
        pts.extend(row)
    faces = []
    for i in range(nstations - 1):
        for k in range(arch):
            a, b = ring[i][k], ring[i][k + 1]
            c, d = ring[i + 1][k + 1], ring[i + 1][k]
            faces.append([a, b, c, d])
    return pts, faces, uvs


def arch_y(x, z):
    """Height of the roof surface at (x, z) on the lofted arch."""
    wz, yf, yr = half_width(x), floor_y(x), roof_y(x)
    s = max(0.0, 1.0 - (z / wz) ** 2)
    return yf + (yr - yf) * math.sqrt(s)


def build_floor(nstations=40, ncross=16):
    """The breccia floor as a fan surface. Returns (points, faces, uvs)."""
    pts, uvs, grid = [], [], []
    for i in range(nstations):
        x = LENGTH * i / (nstations - 1)
        wz, yf = half_width(x), floor_y(x)
        row = []
        for j in range(ncross + 1):
            z = -wz + wz * j / ncross          # back half only: z from -wz to 0
            # rubble undulation + fractal lumpiness on the deposit surface
            bump = 0.8 * math.sin(0.5 * x + 0.9 * j) * math.exp(-((z) / (wz + 1)) ** 2)
            bump += (fbm(x * 0.12, z * 0.18 + 5.0, 9.0) - 0.5) * 1.8
            row.append((x, yf - 0.5 + bump, z))
            uvs.append((x / TEX_FT, z / TEX_FT))
        grid.append([len(pts) + j for j in range(len(row))])
        pts.extend(row)
    faces = []
    for i in range(nstations - 1):
        for j in range(ncross):
            a, b = grid[i][j], grid[i][j + 1]
            c, d = grid[i + 1][j + 1], grid[i + 1][j]
            faces.append([a, b, c, d])
    return pts, faces, uvs


def ifs(points, faces, solid="false", colors=None, crease=1.2, uvs=None):
    cattr = ' colorPerVertex="true"' if colors else ''
    cnode = f'<Color color="{fmt_cols(colors)}"/>' if colors else ''
    tnode = f'<TextureCoordinate point="{fmt_uvs(uvs)}"/>' if uvs else ''
    return (f'<IndexedFaceSet solid="{solid}" creaseAngle="{crease}"{cattr} '
            f'coordIndex="{fmt_idx(faces)}">'
            f'<Coordinate point="{fmt_pts(points)}"/>{cnode}{tnode}</IndexedFaceSet>')


# ---------------------------------------------------------------------------
# speleothems -- stalactites, stalagmites, columns, flowstone drapery
# ---------------------------------------------------------------------------

def _dripstone(cx, cy, cz, length, radius, flip, mat, segs=7):
    """A tapered, slightly irregular dripstone spike as an IndexedFaceSet.

    flip=False: stalagmite (wide base at cy, taper up). flip=True: stalactite
    (wide base at cy, taper down).
    """
    sign = -1.0 if flip else 1.0
    rings, pts = [], []
    nseg, nc = segs, 9
    for s in range(nseg + 1):
        t = s / nseg
        y = cy + sign * length * t
        # taper to a point, with a couple of bulges (flowstone banding)
        rad = radius * (1.0 - t) ** 1.3 * (1.0 + 0.18 * math.sin(6.0 * t))
        rad = max(rad, 0.02)
        wob = 0.12 * radius * math.sin(3.0 * t + cx)
        row = []
        for j in range(nc + 1):
            a = 2.0 * math.pi * j / nc
            row.append((cx + (rad) * math.cos(a) + wob,
                        y,
                        cz + (rad) * math.sin(a)))
        rings.append([len(pts) + k for k in range(len(row))])
        pts.extend(row)
    faces = []
    for s in range(nseg):
        for j in range(nc):
            a, b = rings[s][j], rings[s][j + 1]
            c, d = rings[s + 1][j + 1], rings[s + 1][j]
            faces.append([a, b, c, d])
    return f'<Shape>{mat}{ifs(pts, faces, solid="true", crease=1.0)}</Shape>'


def stalactites(mat):
    out = []
    x = 6.0
    while x < LENGTH - 5:
        z = -(1.5 + 7.0 * hash01(x, 3.3))
        if abs(z) > half_width(x) - 1.5:
            z = -(half_width(x) - 1.5)
        top = arch_y(x, z)
        length = 1.8 + 7.0 * hash01(x, 1.1)
        rad = 0.35 + 0.9 * hash01(x, 2.2)
        if top - length > floor_y(x) + 1:        # don't pierce the floor
            out.append(_dripstone(x, top - 0.3, z, length, rad, True, mat))
        x += 4.0 + 4.0 * hash01(x, 9.0)
    return "".join(out)


def stalagmites(mat):
    out = []
    # cluster on and around the two breccia fans
    for cxc in (NW_FAN_X, SE_FAN_X):
        n = 6
        for i in range(n):
            x = cxc + (hash01(cxc, i) - 0.5) * 34
            x = max(6.0, min(LENGTH - 6.0, x))
            z = -(1.0 + 6.0 * hash01(x, i + 4))
            if abs(z) > half_width(x) - 1.0:
                continue
            base = floor_y(x) - 0.5
            length = 1.2 + 4.6 * hash01(x, i + 7)
            rad = 0.4 + 0.9 * hash01(x, i + 2)
            out.append(_dripstone(x, base, z, length, rad, False, mat))
    return "".join(out)


def flowstone_drape(mat):
    """A draped flowstone sheet on the back wall near the SE end."""
    x0, span = 92.0, 12.0
    nx, ny = 10, 7
    pts, grid = [], []
    for iy in range(ny + 1):
        ty = iy / ny
        for ix in range(nx + 1):
            tx = ix / nx
            x = x0 + span * tx
            z = -(half_width(x) - 1.2)
            top = arch_y(x, z)
            y = top - (top - floor_y(x) - 1.0) * ty
            drape = 0.6 * math.sin(9.0 * tx + 1.5 * ty) * (1.0 - ty)
            pts.append((x, y, z + 1.2 + drape))
        grid.append([(ny + 1 - 0) ])  # placeholder, rebuilt below
    # rebuild index grid cleanly
    grid = [[iy * (nx + 1) + ix for ix in range(nx + 1)] for iy in range(ny + 1)]
    faces = []
    for iy in range(ny):
        for ix in range(nx):
            a, b = grid[iy][ix], grid[iy][ix + 1]
            c, d = grid[iy + 1][ix + 1], grid[iy + 1][ix]
            faces.append([a, b, c, d])
    return f'<Shape>{mat}{ifs(pts, faces, solid="false", crease=1.5)}</Shape>'


def shaft(cx, cz, base_y, height, radius, color, opacity="1"):
    """A vertical chimney/pit shaft as a Transform-wrapped Cylinder."""
    cy = base_y + height / 2.0
    return (f'<Transform translation="{fnum(cx)} {fnum(cy)} {fnum(cz)}">'
            f'<Shape><Appearance><Material diffuseColor="{color}" '
            f'emissiveColor="{color}" ambientIntensity="0.2"/>'
            f'</Appearance><Cylinder height="{fnum(height)}" radius="{fnum(radius)}" '
            f'side="true" top="false" bottom="false"/></Shape></Transform>')


def strat_column(cx, cz):
    """Banded stratigraphic cut of the NW fan, in Sinclair's (1904) documented
    sequence (bottom-up): cemented breccia, ~1.5 ft volcanic ash, upper clay to
    ~13.5 ft. Thicknesses scaled down so the band column fits the section."""
    # (label, thickness ft, color) bottom-up -- matches the cited NW-fan section
    bands = [
        ("cemented breccia", 5.0, "0.32 0.24 0.18"),
        ("volcanic ash",     1.5, "0.78 0.76 0.70"),
        ("upper clay",       6.5, "0.5 0.38 0.28"),
    ]
    out = ['<Group>']
    y = floor_y(cx) - sum(b[1] for b in bands)   # sink the column into the fan
    w, depth = 5.0, 5.0
    for name, th, col in bands:
        cy = y + th / 2.0
        out.append(
            f'<Transform translation="{fnum(cx)} {fnum(cy)} {fnum(cz)}">'
            f'<Shape><Appearance><Material diffuseColor="{col}" ambientIntensity="0.5"/>'
            f'</Appearance><Box size="{fnum(w)} {fnum(th)} {fnum(depth)}"/></Shape>'
            f'</Transform>')
        y += th
    out.append('</Group>')
    return "".join(out)


def scale_figure(cx, cz):
    """A 6 ft human proxy standing on the floor for scale."""
    fy = floor_y(cx) - 0.5
    body_h, head_r = 5.2, 0.45
    by = fy + body_h / 2.0
    hy = fy + body_h + head_r
    mat = ('<Appearance><Material diffuseColor="0.88 0.52 0.2" '
           'emissiveColor="0.18 0.09 0.02" ambientIntensity="0.6"/></Appearance>')
    return (
        f'<Group>'
        f'<Transform translation="{fnum(cx)} {fnum(by)} {fnum(cz)}"><Shape>{mat}'
        f'<Cylinder height="{fnum(body_h)}" radius="0.55"/></Shape></Transform>'
        f'<Transform translation="{fnum(cx)} {fnum(hy)} {fnum(cz)}"><Shape>{mat}'
        f'<Sphere radius="{fnum(head_r)}"/></Shape></Transform>'
        f'</Group>')


def look_orientation(eye, target):
    """Axis-angle rotation taking the default -Z view to look at target."""
    dx, dy, dz = (target[0] - eye[0], target[1] - eye[1], target[2] - eye[2])
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    fx, fy, fz = dx / n, dy / n, dz / n
    # rotate (0,0,-1) -> (fx,fy,fz); axis = cross((0,0,-1), f) = (fy, -fx, 0)
    ax, ay, az = (fy, -fx, 0.0)
    al = math.sqrt(ax * ax + ay * ay + az * az)
    if al < 1e-6:
        return "0 1 0 0"
    ax, ay, az = ax / al, ay / al, az / al
    ang = math.acos(max(-1.0, min(1.0, -fz)))
    return f"{fnum(ax)} {fnum(ay)} {fnum(az)} {fnum(ang)}"


# ---------------------------------------------------------------------------
# assemble scene
# ---------------------------------------------------------------------------

def column(cx, cz, mat, segs=12, nc=11):
    """A floor-to-roof column where a stalactite and stalagmite have fused."""
    base, top = floor_y(cx) - 0.4, arch_y(cx, cz)
    H = max(top - base, 2.0)
    rmax = 0.7 + 0.6 * hash01(cx, 7.0)
    rings, pts = [], []
    for s in range(segs + 1):
        t = s / segs
        y = base + H * t
        # wide at both ends, slim waist, with flowstone banding
        prof = 0.45 + 0.55 * abs(math.cos(math.pi * t))
        rad = rmax * prof * (1.0 + 0.14 * math.sin(9.0 * t + cx))
        row = []
        for j in range(nc + 1):
            a = 2.0 * math.pi * j / nc
            row.append((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
        rings.append([len(pts) + k for k in range(len(row))])
        pts.extend(row)
    faces = []
    for s in range(segs):
        for j in range(nc):
            faces.append([rings[s][j], rings[s][j + 1],
                          rings[s + 1][j + 1], rings[s + 1][j]])
    return f'<Shape>{mat}{ifs(pts, faces, solid="true", crease=1.0)}</Shape>'


def drapery(x0, span, mat, nx=12, ny=8):
    """A folded flowstone curtain hanging from the roof (thin wavy sheet)."""
    pts, grid = [], []
    for iy in range(ny + 1):
        ty = iy / ny
        for ix in range(nx + 1):
            tx = ix / nx
            x = x0 + span * tx
            z = -(half_width(x) - 1.4)
            top = arch_y(x, z)
            y = top - (top - floor_y(x) - 2.0) * ty
            fold = 0.9 * math.sin(7.0 * tx) * (1.0 - 0.5 * ty)
            pts.append((x, y, z + 1.4 + fold))
        grid.append([iy * (nx + 1) + ix for ix in range(nx + 1)])
    faces = []
    for iy in range(ny):
        for ix in range(nx):
            a, b = grid[iy][ix], grid[iy][ix + 1]
            c, d = grid[iy + 1][ix + 1], grid[iy + 1][ix]
            faces.append([a, b, c, d])
    return f'<Shape>{mat}{ifs(pts, faces, solid="false", crease=1.6)}</Shape>'


def breakdown(mat, n=11):
    """Angular fallen-rock blocks (breakdown) scattered on the floor."""
    out = []
    for i in range(n):
        x = 9.0 + 90.0 * hash01(i, 1.0)
        wz = half_width(x)
        z = -(1.0 + (wz - 2.5) * hash01(i, 2.0))
        y = floor_y(x) - 0.2
        s = 1.3 + 3.2 * hash01(i, 3.0)
        sx = s * (0.7 + 0.6 * hash01(i, 4.0))
        sy = s * (0.4 + 0.5 * hash01(i, 5.0))
        sz = s * (0.6 + 0.6 * hash01(i, 6.0))
        ang = 6.2832 * hash01(i, 7.0)
        ax, ay, az = hash01(i, 8.0), 0.3 + hash01(i, 9.0), hash01(i, 10.0)
        out.append(
            f'<Transform translation="{fnum(x)} {fnum(y)} {fnum(z)}" '
            f'rotation="{fnum(ax)} {fnum(ay)} {fnum(az)} {fnum(ang)}">'
            f'<Shape>{mat}<Box size="{fnum(sx)} {fnum(sy)} {fnum(sz)}"/></Shape>'
            f'</Transform>')
    return "".join(out)


def pool(cx, cz, r, mat):
    """A reflective standing-water disc (the cave's quiet pools)."""
    return (f'<Transform translation="{fnum(cx)} {fnum(floor_y(cx) - 0.3)} {fnum(cz)}" '
            f'rotation="1 0 0 1.5707"><Shape>{mat}'
            f'<Cylinder height="0.15" radius="{fnum(r)}" top="true" '
            f'side="false" bottom="false"/></Shape></Transform>')


def daylight_shaft(cx, cz):
    """A god-ray down the entrance pit: nested translucent cones + dust motes.

    Faked volumetrics -- X3D has no participating-media scattering, so the beam
    is layered emissive cones (brighter core) with drifting motes for life.
    """
    top, bot = roof_y(cx) + 4.0, floor_y(cx)
    h = top - bot
    cy = (top + bot) / 2.0
    out = [f'<Transform translation="{fnum(cx)} {fnum(cy)} {fnum(cz)}">']
    for rad, em, tr in ((8.0, "0.34 0.45 0.62", 0.94),
                        (5.0, "0.5 0.62 0.8", 0.9),
                        (2.6, "0.7 0.82 1", 0.84)):
        out.append(
            f'<Shape><Appearance><Material emissiveColor="{em}" '
            f'transparency="{tr}"/></Appearance>'
            f'<Cone bottomRadius="{fnum(rad)}" height="{fnum(h)}" '
            f'side="true" bottom="false"/></Shape>')
    out.append('</Transform>')
    # dust motes drifting in the shaft
    for i in range(14):
        mx = cx + (hash01(i, 1.1) - 0.5) * 9
        my = bot + h * hash01(i, 2.2)
        mz = cz + (hash01(i, 3.3) - 0.5) * 7
        out.append(
            f'<Transform translation="{fnum(mx)} {fnum(my)} {fnum(mz)}">'
            f'<Shape><Appearance><Material emissiveColor="0.8 0.86 1" '
            f'transparency="0.25"/></Appearance>'
            f'<Sphere radius="{fnum(0.08 + 0.12 * hash01(i, 4.4))}"/></Shape></Transform>')
    return "".join(out)


def _pbr_rock(tint):
    """PhysicalMaterial limestone: albedo + tangent-space normal + roughness.
    metallic=0 (rock); roughness=1 lets the MR texture's green channel drive it."""
    return (
        f'<Appearance><PhysicalMaterial baseColor="{tint}" metallic="0" '
        f'roughness="1" normalScale="1.6">'
        f'<ImageTexture url=\'"cave_textures/limestone_albedo.png"\' '
        f'containerField="baseTexture"/>'
        f'<ImageTexture url=\'"cave_textures/limestone_normal.png"\' '
        f'containerField="normalTexture"/>'
        f'<ImageTexture url=\'"cave_textures/limestone_mr.png"\' '
        f'containerField="metallicRoughnessTexture"/>'
        f'</PhysicalMaterial></Appearance>')


def build_scene():
    sp, sf, su = build_shell()
    fp, ff, fu = build_floor()

    # normal-mapped, displaced PBR limestone (walls slightly cool, floor warmer)
    limestone = _pbr_rock("0.92 0.9 0.84")
    breccia = _pbr_rock("0.6 0.45 0.32")
    # wet, banded flowstone: lighter, more specular than the dry wall
    flowstone = ('<Appearance><Material diffuseColor="0.62 0.58 0.5" '
                 'specularColor="0.35 0.34 0.3" shininess="0.55" '
                 'ambientIntensity="0.22"/></Appearance>')
    rubble = ('<Appearance><Material diffuseColor="0.38 0.3 0.23" '
              'specularColor="0.04 0.035 0.03" ambientIntensity="0.2"/></Appearance>')
    # rippled PBR water: low roughness reflections + a ripple normal map; the
    # transparency reads as shallow refraction (true refraction isn't in X3D).
    water = ('<Appearance><PhysicalMaterial baseColor="0.06 0.16 0.2" metallic="0" '
             'roughness="0.08" transparency="0.35" normalScale="0.6">'
             '<ImageTexture url=\'"cave_textures/water_normal.png"\' '
             'containerField="normalTexture"/></PhysicalMaterial></Appearance>')
    beam = ('<Appearance><Material emissiveColor="0.4 0.52 0.72" '
            'transparency="0.9"/></Appearance>')

    eye = (LENGTH * 0.5, 54.0, 126.0)       # in front of the open section, raised
    tgt = (LENGTH * 0.5, 30.0, -6.0)
    orient = look_orientation(eye, tgt)
    # hero: head-on, zoomed to the NW third -- entrance pit shaft, fan, columns
    hero = (32.0, 50.0, 96.0)
    hero_o = look_orientation(hero, (32.0, 31.0, -6.0))

    parts = []
    parts.append(f'<Shape>{limestone}{ifs(sp, sf, uvs=su)}</Shape>')
    parts.append(f'<Shape>{breccia}{ifs(fp, ff, solid="false", uvs=fu)}</Shape>')

    # speleothems + cave-floor detail (all interpretive -- see PROVENANCE)
    parts.append(stalactites(flowstone))
    parts.append(stalagmites(flowstone))
    parts.append(flowstone_drape(flowstone))
    parts.append(drapery(60.0, 14.0, flowstone))
    parts.append(column(40.0, -5.0, flowstone))
    parts.append(column(73.0, -6.5, flowstone))
    parts.append(breakdown(rubble))
    # quiet pools in the low spots between and beside the fans
    parts.append(pool(53.0, -5.0, 6.0, water))
    parts.append(pool(64.0, -9.0, 3.2, water))
    parts.append(pool(22.0, -7.0, 2.6, water))
    # a shaft of daylight falling down the great entrance pit
    parts.append(daylight_shaft(PIT_X, -3.0))

    # chimneys above each fan apex (in the back wall, z slightly negative)
    parts.append(shaft(NW_FAN_X, -3, roof_y(NW_FAN_X) - 4, 34, 3.2, "0.05 0.05 0.06"))
    parts.append(shaft(SE_FAN_X, -3, roof_y(SE_FAN_X) - 4, 30, 2.8, "0.05 0.05 0.06"))
    # the great pit -- 42 ft entrance descent near the NW end
    parts.append(shaft(PIT_X, -3, roof_y(PIT_X) - 6, 42, 4.0, "0.04 0.04 0.05"))

    parts.append(strat_column(NW_FAN_X + 6, -6))
    parts.append(scale_figure(LENGTH * 0.52, -4))

    # lights: a soft daylight wash from the open section + warm lantern pools.
    # Headlight is OFF (NavigationInfo) so the cave keeps its depth and shadow.
    lights = (
        '<DirectionalLight direction="0.1 -0.5 -1" intensity="0.6" color="0.82 0.86 0.96"/>'
        '<DirectionalLight direction="-0.2 -1 0.1" intensity="0.2" color="0.55 0.58 0.68"/>'
        f'<PointLight location="{fnum(PIT_X)} {fnum(floor_y(PIT_X)+6)} -3" '
        'color="1 0.83 0.5" intensity="0.6" radius="48" attenuation="1 0.03 0.004"/>'
        f'<PointLight location="{fnum(NW_FAN_X)} {fnum(floor_y(NW_FAN_X)+5)} -3" '
        'color="1 0.78 0.46" intensity="0.5" radius="42" attenuation="1 0.04 0.006"/>'
        f'<PointLight location="{fnum(SE_FAN_X)} {fnum(floor_y(SE_FAN_X)+5)} -3" '
        'color="1 0.8 0.48" intensity="0.5" radius="42" attenuation="1 0.04 0.006"/>'
        # cool daylight spilling down the 42 ft entrance pit where the party descended
        f'<PointLight location="{fnum(PIT_X)} {fnum(roof_y(PIT_X)+20)} -3" '
        'color="0.7 0.8 1" intensity="0.9" radius="55" attenuation="1 0.02 0.002"/>'
    )

    scene = (
        f'<Background skyColor="0.02 0.02 0.03 0.04 0.04 0.05" '
        f'groundColor="0.02 0.02 0.02" skyAngle="1.2"/>'
        # faint atmospheric haze (kept subtle -- the section is shallow in depth)
        f'<Fog fogType="LINEAR" color="0.04 0.04 0.05" visibilityRange="520"/>'
        f'<NavigationInfo type=\'"EXAMINE" "WALK" "ANY"\' headlight="false" '
        f'avatarSize="0.5 6 0.75" speed="12"/>'
        f'<Viewpoint DEF="Section" description="Down the chamber from the entrance" '
        f'position="{fnum(eye[0])} {fnum(eye[1])} {fnum(eye[2])}" '
        f'orientation="{orient}" fieldOfView="1.05"/>'
        f'<Viewpoint DEF="Hero" description="Hero -- the entrance fan and daylight shaft" '
        f'position="{fnum(hero[0])} {fnum(hero[1])} {fnum(hero[2])}" '
        f'orientation="{hero_o}" fieldOfView="0.95"/>'
        f'<Viewpoint DEF="Plan" description="Plan / overhead" position="53 130 1" '
        f'orientation="1 0 0 -1.5707" fieldOfView="0.9"/>'
        f'{lights}'
        f'<Group>{"".join(parts)}</Group>'
    )
    return scene


def x3d_doc(scene):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" '
        '"https://www.web3d.org/specifications/x3d-4.0.dtd">\n'
        '<X3D profile="Immersive" version="4.0" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" '
        'xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">\n'
        '<head>\n'
        '<meta name="title" content="Potter Creek Cave"/>\n'
        '<meta name="description" content="To-scale model from Sinclair (1904), '
        'excavation directed by John C. Merriam. Shasta County, California."/>\n'
        '<meta name="reference" content="Sinclair, W.J. (1904) The Exploration of '
        'Potter Creek Cave. Univ. Calif. Publ. Amer. Arch. Ethn. 2(1)."/>\n'
        '<meta name="creator" content="x3d_mcp cave pipeline"/>\n'
        '</head>\n'
        f'<Scene>\n{scene}\n</Scene>\n</X3D>\n'
    )


XITE_VER = "15.1.4"          # pinned (was @latest); X_ITE renders the PBR

# Shown instead of a black screen when the page is opened from file:// -- X_ITE
# fetches the .x3d over http and the browser blocks that over file://.
FILE_GUARD = """<script>
if (location.protocol === 'file:') {
  window.addEventListener('DOMContentLoaded', function () {
    document.body.style.cssText = 'margin:0;height:100vh;display:flex;align-items:'
      + 'center;justify-content:center;background:#0a0a0c;color:#cdbfa6;'
      + 'font-family:Georgia,serif;text-align:center';
    document.body.innerHTML = '<div style="max-width:540px;padding:24px;line-height:1.6">'
      + '<h2 style="color:#e9d9b8">Start the local viewer</h2>'
      + '<p>This 3-D viewer loads its data over <b>http</b>. Browsers block the '
      + 'renderer from reading 3-D files over <code>file://</code>, so opening this '
      + 'page by double-click shows nothing.</p>'
      + '<p>In Terminal, from the project folder, run:</p>'
      + '<p style="background:#1d1a14;padding:10px 16px;border-radius:6px;'
      + 'display:inline-block;font-family:monospace">./start_caves.sh</p>'
      + '<p>It serves the folder and opens '
      + '<b>http://127.0.0.1:8099/caves.html</b> for you.</p></div>';
  });
}
</script>"""

POTTER_CAP = (
    '<b>Potter Creek Cave</b>, Shasta County, CA &mdash; to scale from '
    'W.&nbsp;J.&nbsp;Sinclair, <i>The Exploration of Potter Creek Cave</i> (1904), '
    'excavation directed by John&nbsp;C.&nbsp;Merriam. Chamber 107&nbsp;ft long, '
    'roof ~75&nbsp;ft; two coalescing breccia fans, chimneys, the 42&nbsp;ft '
    'entrance pit. <span style="opacity:.8">Chamber, fans, chimneys and the pit '
    'are to scale from the 1904 survey; speleothems, pools, rock texture and '
    'lighting are interpretive.</span> Drag to orbit.'
)


def xite_html(title, src, caption):
    """A guarded, version-pinned X_ITE viewer page."""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
{FILE_GUARD}
<script src="https://cdn.jsdelivr.net/npm/x_ite@{XITE_VER}/dist/x_ite.min.js"></script>
<style>
 html,body{{margin:0;background:#08080a;color:#cdbfa6;font-family:Georgia,serif}}
 x3d-canvas,canvas{{width:100vw;height:100vh;display:block}}
 .cap{{position:fixed;left:18px;bottom:14px;max-width:540px;font-size:13px;
   line-height:1.45;text-shadow:0 1px 3px #000;z-index:10}}
 .cap b{{color:#e9d9b8}}
 .home{{position:fixed;left:18px;top:14px;font-size:13px;z-index:10}}
 .home a{{color:#cdbfa6;opacity:.75;text-decoration:none}}
</style></head>
<body>
<x3d-canvas src="{src}"></x3d-canvas>
<div class="home"><a href="caves.html">&larr; all caves</a></div>
<div class="cap">{caption}</div>
</body></html>
"""


def main():
    scene = build_scene()
    with open("potter_creek_cave.x3d", "w") as f:
        f.write(x3d_doc(scene))
    with open("potter_creek_cave_xite.html", "w") as f:
        f.write(xite_html("Potter Creek Cave", "potter_creek_cave.x3d", POTTER_CAP))
    with open("potter_creek_cave_hero.html", "w") as f:
        f.write(xite_html("Potter Creek Cave — hero",
                          "potter_creek_cave.x3d#Hero", POTTER_CAP))
    print("wrote potter_creek_cave.x3d + xite/hero viewer pages")


if __name__ == "__main__":
    main()
