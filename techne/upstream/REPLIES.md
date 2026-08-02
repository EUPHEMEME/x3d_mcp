# Draft replies — ready to paste

Attach the matching test from this directory to each thread.

---

## 1 → Python-SAI issue #3 (EnvironmentLight.global)

Thank you — and you are right about `global`.

**Withdrawing the original argument.** The issue as I filed it reasoned from a
commented-out `FALSE` in the 4.0 stub, and that reasoning does not hold:
`EnvironmentLight` is a 4.1 node, its `global` default is `TRUE` in 4.1, and the
code you quoted implements that correctly. Nothing to fix there.

What remains is a different and I think more checkable problem, in two parts.
`X3DSerializationValidityTest.py` (attached) covers both, isolating each from
the other. It needs `xmllint` and a local `x3d-4.0.xsd`.

### A. `xmlns:xsd` is `https://` and needs to be `http://`

This one affects **every** document x3d.py writes, not just lighting. Current
output:

```xml
<X3D profile='Immersive' version='4.0'
     xmlns:xsd='https://www.w3.org/2001/XMLSchema-instance'
     xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>
```

The canonical namespace name is `http://www.w3.org/2001/XMLSchema-instance`.
Namespace names are matched by literal string comparison rather than resolved as
URLs, so the `https` form is a different namespace and
`xsd:noNamespaceSchemaLocation` stops being the schema-instance attribute:

```
element X3D: Schemas validity error : Element 'X3D', attribute
'{https://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation':
The attribute ... is not allowed.
```

A document containing nothing but a `DirectionalLight` fails this way. Changing
that one character, and nothing else, makes the same bytes validate — the test
does exactly that substitution as its isolation step, so the diagnosis does not
rest on my reading.

(The `schemaLocation` *value* pointing at `https://www.web3d.org/...` is fine —
that one really is a URL and is fetched. It is only the namespace name that must
stay `http`.)

### B. A 4.1-only node is emitted into a document declared 4.0

`EnvironmentLight(DEF='ibl', global_=True)` inside an `X3D(version='4.0')`
produces a document whose header declares `version='4.0'`, whose DOCTYPE is
`ISO//Web3D//DTD X3D 4.0//EN`, and which cites `x3d-4.0.xsd` — while containing a
node that is commented out of that schema under `deferred until X3D 4.1`. With
defect A neutralised, the remaining error is:

```
element EnvironmentLight: Schemas validity error :
Element 'EnvironmentLight': This element is not expected.
```

No warning is issued at construction or serialization.

I would not describe the default-dropping as a bug: dropping a field whose value
equals the default is correct canonicalisation. It is just that here it removes
the one attribute that would have made the version mismatch visible, so the
author gets a 4.0 file, a 4.0 validator, and no signal. A version check at
serialization would surface it cheaply.

**How I was rendering:** X_ITE (`create3000.github.io/x_ite/`) in headless
Chromium via Playwright, comparing rendered frames with and without the node. The
scene came back visually unlit while validating clean, which is what sent me
looking.

---

## 2 → SourceForge ticket #117 (HAnim XML output)

Attached is `HAnimContainerFieldTest.py` — a six-node reduction of the JinLOA1.py
failure, small enough to run in CI without the full model. It reproduces all
three problems you noted, plus one more, asserting each separately so a partial
fix reports precisely what remains.

Output on x3d.py 4.0.65.3:

```xml
<HAnimHumanoid DEF='hanim_Test' name='Test'>
  <HAnimSegment USE='hanim_sacrum'/>
  <HAnimJoint DEF='hanim_humanoid_root' name='humanoid_root'>
    <HAnimSegment DEF='hanim_sacrum' name='sacrum'/>
  </HAnimJoint>
</HAnimHumanoid>
```

from:

```python
X.HAnimHumanoid(DEF="hanim_Test", name="Test", version="2.0",
    skeleton=[X.HAnimJoint(DEF="hanim_humanoid_root", name="humanoid_root",
                children=[X.HAnimSegment(DEF="hanim_sacrum", name="sacrum")])],
    segments=[X.HAnimSegment(USE="hanim_sacrum")])
```

1. **`containerField` omitted on non-default slots.** The joint was placed in
   `skeleton`, the segment in `segments`; neither is serialized with a
   `containerField`, so on reparse both land in `children`. `HAnimHumanoid` has
   six node fields and only one is the default, so this is the common case. It is
   silent — every node is still present and the document still validates; the
   skeleton just is not a skeleton.

2. **`USE` precedes its `DEF`.** `USE='hanim_sacrum'` at offset 61,
   `DEF='hanim_sacrum'` at 162 — a forward reference in a format read in
   document order.

3. **`version='2.0'` dropped.** Set on the object and retained there
   (`obj.version == '2.0'`), absent from the XML. Not in the ticket text, but
   your own "expected output" excerpt carries `version='2.0'`.
