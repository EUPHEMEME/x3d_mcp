# Draft replies — ready to paste

Two threads. Both attach the matching test from this directory.

---

## 1 → Python-SAI issue #3 (EnvironmentLight.global)

Thank you — and no apology needed for the reopen.

I think the beta is still affected, and the reason is that the defect is not in
the emit logic itself but in **which schema version that logic is keyed to**.

From the two schemas as published:

| schema | `EnvironmentLight` `global` default |
|---|---|
| `x3d-4.0.xsd` | **`false`** |
| `x3d-4.1.xsd` | **`true`** |

For contrast, `PointLight` is `true` and `DirectionalLight` is `false` in *both*.
`EnvironmentLight` appears to be the only light whose default moved between the
two — which I suspect is the substance of Mantis 1539.

The line you quoted:

```python
if self.USE=="" and not self.global_:   # default=true
    result += " global='" + SFBool(self.global_).XML() + "'"
```

is exactly right **for a document that declares X3D 4.1**. It omits the
attribute when the value equals the assumed default of `true`. But x3d.py emits
a 4.0 header by default:

```xml
<!DOCTYPE X3D PUBLIC "ISO//Web3D//DTD X3D 4.0//EN" ...>
<X3D profile='Immersive' version='4.0'
     xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>
  <Scene>
    <EnvironmentLight DEF='ibl'/>
  </Scene>
</X3D>
```

That is the output for `EnvironmentLight(DEF='ibl', global_=True)`. The document
declares 4.0 and cites `x3d-4.0.xsd`, where the default is `false` — so a
conforming 4.0 reader scopes the light to its parent and image-based lighting
disappears. No error is raised at any stage, because an absent attribute is
valid under either schema.

What makes it easy to miss: **round-tripping through x3d.py hides it**, since
the reader applies the same assumed default the writer used. It only shows up in
a different conforming reader.

So the fix is conditional on the declared version rather than absolute — emit
`global` whenever it is `True` for a 4.0 document, or keep the current rule and
emit a 4.1 header.

**Test program:** `EnvironmentLightGlobalTest.py` (attached). Stdlib + x3d.py,
self-asserting, exits non-zero. It prints the in-memory default, both schema
defaults, and the emitted document, then fails on the two conditions that
matter. It should simply pass once this is resolved either way.

**How I was rendering:** X_ITE (`create3000.github.io/x_ite/`) in a headless
Chromium via Playwright, comparing rendered frames with and without the node. I
first noticed it because a scene lit only by an `EnvironmentLight` came back
visually unlit while the document validated clean.

Happy to supply a full exemplar scene if the minimal case above is not enough —
I kept the test to six lines of construction so it is cheap to run in CI.

---

## 2 → SourceForge ticket #117 (HAnim XML output)

Attached is `HAnimContainerFieldTest.py` — a six-node reduction of the JinLOA1.py
failure, written so it runs in CI without the full model. It reproduces all three
problems you noted, plus one more.

Output on x3d.py 4.0.65.3:

```xml
<HAnimHumanoid DEF='hanim_Test' name='Test'>
  <HAnimSegment USE='hanim_sacrum'/>
  <HAnimJoint DEF='hanim_humanoid_root' name='humanoid_root'>
    <HAnimSegment DEF='hanim_sacrum' name='sacrum'/>
  </HAnimJoint>
</HAnimHumanoid>
```

built from:

```python
X.HAnimHumanoid(DEF="hanim_Test", name="Test", version="2.0",
    skeleton=[X.HAnimJoint(DEF="hanim_humanoid_root", name="humanoid_root",
                children=[X.HAnimSegment(DEF="hanim_sacrum", name="sacrum")])],
    segments=[X.HAnimSegment(USE="hanim_sacrum")])
```

1. **`containerField` omitted on non-default slots.** The joint was placed in
   `skeleton` and the segment in `segments`; neither is serialized with a
   `containerField`, so on reparse both land in `children`. `HAnimHumanoid` has
   six node fields and only one is the default, so this is the common case
   rather than an edge case. It is silent: the nodes are all still present and
   the document is still schema-valid — the skeleton just is not a skeleton.

2. **`USE` precedes its `DEF`.** `USE='hanim_sacrum'` is emitted at offset 61,
   `DEF='hanim_sacrum'` at 162 — a forward reference in a format read in
   document order.

3. **`version='2.0'` dropped.** Set on the object and retained there
   (`obj.version == '2.0'`), absent from the XML. This one is not in the ticket
   text but is visible in your own "expected output" excerpt, which carries
   `version='2.0'`.

The test asserts each separately so a partial fix still reports precisely what
remains.
