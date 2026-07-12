<!-- EARMARKED: include with the email to Don Brutzman (Web3D) alongside the
     demo contribution + LaTeX chatlog PDF. Candidate venue for the demo:
     X3dForAdvancedModeling/LargeLanguageModels/ (per Don's invitation). -->

# x3d.py bug report: dropped `containerField`, wrong `EnvironmentLight.global` default, and undeclared X3D components

**Package:** x3d.py (banner: `x3d.py package 4.0.65.3`)
**Python:** 3.12
**Installed:** `pip install x3d`
**Reporter context:** building HAnim humanoids and PBR scenes programmatically,
serialized with `X3D(...).XML()`, then rendered in Castle Model Viewer and
validated against the X3D 4.0 schema.

Three issues cause valid-looking output that renders incorrectly — or not at all —
in conformant players. All three are in XML serialization.

(Numbering is not contiguous: it follows a working catalog of X3D silent-failure
modes, two of which — interpolator `key`/`keyValue` arity and USE-before-DEF
ordering — are authoring faults rather than x3d.py serializer bugs, so they are not
reproduced here.)

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

## Bug 5 — no `<component>` is ever declared, so HAnim scenes are discarded on load; and `create_scene(profile=…)` is silently dropped

Two divergences that compound into the widest silent failure in the set: the
granular authoring API **cannot produce a working HAnim scene**, and nothing
reports it.

### 5a — the profile argument never reaches the header

```python
create_scene(description="…", profile="Interactive")   # accepted
get_scene(encoding="xml")
# -> <X3D profile='Interchange' version='4.1' …>       # Interactive is gone
```

The model states its intent, the server takes the argument, and the serializer
emits `Interchange` regardless. No error, no warning.

### 5b — a node outside the profile is discarded, with its whole subtree

`Interchange` admits 49 node types. It does not admit `HAnimHumanoid`,
`TouchSensor`, `EnvironmentLight` or `PhysicalMaterial`. And the granular API
offers **no way to declare an X3D `<component>`** — `create_scene` takes no
component list, and there is no `add_component` verb. So an HAnim humanoid built
through `create_node`/`add_child` serializes into a document whose profile does
not admit it, and a conformant player discards the humanoid and everything under
it.

`validate_x3d` reports `valid: true` throughout. Profile conformance is simply
not what schema validation checks.

### Reproduction — measured by render, not by argument

A minimal HAnim figure (one joint, one segment, one white `Box`) rendered in
X_ITE 11.6.6 under every combination. Lit pixels, 400×300:

| profile | `<component name='HAnim' level='1'/>` | result |
|---|---|---|
| Interchange | — | **0.0 % — VANISHES** |
| Interchange | yes | 19.8 % — renders |
| Interactive | — | **0.0 % — VANISHES** |
| Immersive | — | **0.0 % — VANISHES** |
| Immersive | yes | 19.8 % — renders |
| Full | — | 19.8 % — renders |

**No profile below `Full` admits HAnim.** Raising the profile is *not* the fix —
and `Immersive` sounding like it covers everything is exactly the trap. The
component declaration is the fix, and it works at any profile.

End-to-end through the real server: the same granular call sequence emits a document
that renders **0.0 %** as serialized, and **17.6 %** once the required `<component>`
declarations are added to the emitted XML. Nothing else changes.

### Diagnosis

The divergence lives **below the wire**: the model has no argument through which to
comply, so this cannot be repaired at the tool-call layer at all. Rejecting the call
would be a false positive — there is nothing the model could do differently.

### Fix

Either (a) make `create_scene` honor its `profile` argument and accept a
component list, or (b) have the serializer derive the required components from
the nodes actually present and declare them.

(b) is straightforward and needs no new spec knowledge: the server already publishes
both halves of the table. `list_profiles` gives each profile's admitted node set, and
`describe_node` gives every node's component and level — so the required declarations
can be **derived** from the nodes a scene actually contains rather than hand-written.

One caution if you implement it: declare each component at the highest level known
for it. An under-declared level silently drops nodes (the failure we are trying to
prevent), while an over-declared level is always legal and merely admits more than
the scene uses. The per-node level metadata is not entirely trustworthy — it reports
`EnvironmentLight`, an X3D 4.0 addition, as `Lighting` level 1.

---

## Minor note (not a bug)
`HAnimHumanoid(version="2.0")` is omitted from output because x3d.py's default
for `version` is already `"2.0"`. That is valid default-omission, but HAnim
files conventionally state `version` explicitly; consider always emitting it
for `HAnimHumanoid`.

---

## Net effect
Programmatically built HAnim humanoids and PBR/IBL scenes serialize to XML that
**passes XSD schema validation** yet renders incorrectly — or not at all. The
errors are in `containerField` routing, a non-spec default, and an undeclared
component: none of which the schema checks.

Bug 5 is the one that admits no argument-level fix at all. A dropped
`containerField` mis-files one node; an undeclared component discards **the entire
humanoid**, and the granular API gives the model no way to prevent it.

Workaround currently in use: post-process the `.XML()` string to inject
`containerField='skeleton'`, `containerField='emissiveTexture'`/`'baseTexture'`,
`global='true'`, and the `<component>` declarations the scene's own nodes require.
