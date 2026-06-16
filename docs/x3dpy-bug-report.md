<!-- EARMARKED: include with the email to Don Brutzman (Web3D) alongside the
     demo contribution + LaTeX chatlog PDF. Candidate venue for the demo:
     X3dForAdvancedModeling/LargeLanguageModels/ (per Don's invitation). -->

# x3d.py bug report: dropped `containerField` and wrong `EnvironmentLight.global` default

**Package:** x3d.py (banner: `x3d.py package 4.0.65.3`)
**Python:** 3.12
**Installed:** `pip install x3d`
**Reporter context:** building HAnim humanoids and PBR scenes programmatically,
serialized with `X3D(...).XML()`, then rendered in Castle Model Viewer and
validated against the X3D 4.0 schema.

Two issues cause valid-looking output that renders incorrectly (or not at all)
in conformant players. Both are in XML serialization.

---

## Bug 1 — `containerField` is not emitted for a node placed in a non-default field

When a node is supplied through a typed field whose `containerField` differs
from that node type's **default** `containerField`, the serializer emits the
child without any `containerField` attribute. Downstream parsers then route the
child into the node's *default* container, which is the wrong field.

This affects every node type that legally appears in more than one parent field:
`HAnimJoint` (default `children`) placed in `skeleton`/`joints`;
`HAnimSegment` (default `children`) placed in `segments`;
`ImageTexture` (default `texture`) placed in `baseTexture`/`emissiveTexture`/
`normalTexture`/etc. of `PhysicalMaterial`/`UnlitMaterial`.

### Reproduction 1a — HAnim skeleton
```python
from x3d import x3d as X
h = X.HAnimHumanoid(DEF="H", name="h", version="2.0",
        skeleton=[X.HAnimJoint(DEF="r", name="humanoid_root",
                  children=[X.HAnimSegment(DEF="s", name="seg")])])
print(h.XML())
```
**Actual:**
```xml
<HAnimHumanoid DEF='H' name='h'>
  <HAnimJoint DEF='r' name='humanoid_root'>      <!-- no containerField -->
    <HAnimSegment DEF='s' name='seg'/>
  </HAnimJoint>
</HAnimHumanoid>
```
**Expected:** the skeleton root joint must carry `containerField='skeleton'`:
```xml
  <HAnimJoint DEF='r' name='humanoid_root' containerField='skeleton'>
```
**Impact:** players that render `HAnimHumanoid` via its `skeleton` field (e.g.
Castle Model Viewer) put the joint in the default `children` field instead and
render **nothing** — the whole humanoid is invisible, with no warning. Confirmed
by screenshot: scene geometry renders, humanoid does not, until
`containerField='skeleton'` is added by hand.

### Reproduction 1b — PBR / unlit textures
```python
from x3d import x3d as X
print(X.Appearance(material=X.UnlitMaterial(emissiveColor=[1,1,1],
        emissiveTexture=X.ImageTexture(url=["t.png"]))).XML())
print(X.Appearance(material=X.PhysicalMaterial(baseColor=[1,1,1],
        baseTexture=X.ImageTexture(url=["t.png"]))).XML())
```
**Actual:**
```xml
<Appearance>
  <UnlitMaterial emissiveColor='1 1 1'>
    <ImageTexture url='"t.png"'/>              <!-- no containerField -->
  </UnlitMaterial>
</Appearance>
<Appearance>
  <PhysicalMaterial baseColor='1 1 1'>
    <ImageTexture url='"t.png"'/>              <!-- no containerField -->
  </PhysicalMaterial>
</Appearance>
```
**Expected:** `containerField='emissiveTexture'` (resp. `'baseTexture'`).
**Impact:** the texture is emitted with `ImageTexture`'s default `containerField`
`texture`, which `PhysicalMaterial`/`UnlitMaterial` do not define as a field, so
it is dropped/ignored and the surface renders untextured — a flat base color
(e.g. a textured chalkboard renders solid white).

### Control (works) — node in its default field
```python
X.HAnimJoint(DEF='j', children=[X.HAnimSegment(DEF='s')]).XML()
# HAnimSegment default containerField IS 'children', so omission is correct here.
```
The bug only appears when the field's container differs from the node default,
which is exactly the case the typed field keyword should disambiguate.

### Diagnosis
After construction, the child object's `containerField` is never set from the
field it was placed in:
```python
j = X.HAnimJoint(DEF="r", name="root")
X.HAnimHumanoid(skeleton=[j])
print(repr(getattr(j, "containerField", "<none>")))   # -> '<none>'
```
**Suggested fix:** when serializing (or when assigning a typed SFNode/MFNode
field), set each child's `containerField` to the field's container name whenever
it differs from the child type's default `containerField`.

Note that x3d.py exposes no `containerField` setter at all — the constructor
rejects a `containerField=` kwarg and a post-construction attribute assignment is
ignored at `XML()` time — which is why string post-processing of the serialized
output is the only available workaround.

---

## Bug 2 — `EnvironmentLight.global` default is `True`, diverging from the X3D 4.0 spec default (`false`)

```python
from x3d import x3d as X
print(repr(X.EnvironmentLight().global_))   # -> True
e = X.EnvironmentLight(); e.global_ = True
print(e.XML())                              # -> <EnvironmentLight/>   (global omitted)
```
The normative X3D 4.0 Lighting component specifies the `EnvironmentLight` field
table as `SFBool [in,out] global FALSE` — i.e. the specified default is
**`false`**. (The x3d-4.0.dtd line `global %SFBool; "false"` agrees, but note it
sits inside a commented-out block in the DTD, so the field table is the primary
authority here.) Because x3d.py's default is `True`, an explicit `global_=True`
equals the internal default and is omitted from output. A conformant reader then
parses the missing attribute as `false`, so the light is **not** global and does
not illuminate the scene as authored.

This is a spec-divergence rather than a flat contradiction: x3d.py's `True`
matches the convention used by the point/spot light nodes and X_ITE's documented
behavior for `EnvironmentLight`, but the normative spec field table specifies
`FALSE` for `EnvironmentLight.global`. The practical problem is that the
divergent default is silently dropped from serialization, so output authored
against x3d.py renders differently in a spec-default reader.

**Expected:** default `global = False` (matching the normative spec field
table); `global_=True` then serializes as `global='true'`.
**Impact:** image-based ambient lighting silently fails; the scene is lit only
by remaining direct lights. Confirmed in Castle Model Viewer; worked only after
`global='true'` was injected post-serialization.

---

## Minor note (not a bug)
`HAnimHumanoid(version="2.0")` is omitted from output because x3d.py's default
for `version` is already `"2.0"`. That is valid default-omission, but HAnim
files conventionally state `version` explicitly; consider always emitting it
for `HAnimHumanoid`.

---

## Net effect
Programmatically built HAnim humanoids and PBR/IBL scenes serialize to XML that
**passes XSD schema validation** yet renders incorrectly, because the errors are
in `containerField` routing and a non-spec default — neither of which the schema
checks. Workaround currently in use: post-process the `.XML()` string to inject
`containerField='skeleton'`, `containerField='emissiveTexture'`/`'baseTexture'`,
and `global='true'`.
