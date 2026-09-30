# differential_probe — recorded run

Run 2026-08-01 on Hétu (macOS, X_ITE 15.1.12 + Playwright headless Chromium).
Exit code 0 = ran, control clean, no defect missed.
This is the end-to-end evidence that the occupation gate's rung above blankness
works against the REAL renderer, not a fake one. Cited by the Web3D 2026 paper.

```
differential_probe v1.0 (2026-07-25)
renderer: src/tools/render.py::_render_xite_async  (X_ITE + Playwright headless Chromium — the same function behind the render_image MCP tool)
frame: 512x384, wait 6000 ms, repo /Users/alexander/x3d_mcp
artifacts: (local scratchpad)

sanity: control renders non-blank (stddev 60.7); identical scene rendered twice differs by 0/196608 px (renderer noise floor; the contribution threshold is 98 px)

── CONTROL — entirely correct scene: every node must contribute
   components injected by reassert_profile: none
      DirectionalLight  KeyLight       43264 / 196608  px   22.01%  -> CONTRIBUTES
      Shape             Subject        43264 / 196608  px   22.01%  -> CONTRIBUTES
      ImageTexture      ControlTex     43264 / 196608  px   22.01%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   verdict: CLEAN — no false positives

── CASE 1. HAnim skeleton containerField
   defect: x3d.py Bug 1 — joint routed into 'children' instead of 'skeleton'
   components injected by reassert_profile: ["<component name='HAnim' level='2'/>"]
   note: Bug 5 is controlled: craft.reassert_profile injected the HAnim component declaration into BOTH variants (shown above), so the only difference left inside the pair is the containerField. 'Torso' rides inside the discarded joint, so expect it absent too in the defective variant — same root cause, two reported nodes.
   variant: correct    (frame non-blank: True, stddev 49.8 — the blank gate passes this frame)
      Shape             Pedestal        7068 / 196608  px    3.59%  -> CONTRIBUTES
      HAnimHumanoid     Human           7744 / 196608  px    3.94%  -> CONTRIBUTES
      Shape             Torso           7744 / 196608  px    3.94%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   variant: defective  (frame non-blank: True, stddev 20.2 — the blank gate passes this frame)
      Shape             Pedestal        7068 / 196608  px    3.59%  -> CONTRIBUTES
      HAnimHumanoid     Human              0 / 196608  px    0.00%  -> ABSENT
      Shape             Torso              0 / 196608  px    0.00%  -> ABSENT
      (threshold: >= 98 changed px of 196608 to count as contributing)
   pair verdict: SEPARATED — correct variant contributes 7744 px; defective contributes 0 px — the differential catches this defect deterministically
   correction the check would emit:
      'Human' (HAnimHumanoid) is in the document but draws nothing: the humanoid is invisible. The usual cause is a skeleton root joint routed into 'children' instead of containerField='skeleton' (x3d.py Bug 1); also check the HAnim component is declared and that skin/segments carry geometry.

── CASE 2. PBR baseTexture containerField
   defect: ImageTexture in the default 'texture' slot, which PhysicalMaterial does not define
   components injected by reassert_profile: ["<component name='Shape' level='5'/>"]
   variant: correct    (frame non-blank: True, stddev 27.1 — the blank gate passes this frame)
      Shape             TexturedBox    86434 / 196608  px   43.96%  -> CONTRIBUTES
      ImageTexture      BaseTex        86434 / 196608  px   43.96%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   variant: defective  (frame non-blank: True, stddev 40.2 — the blank gate passes this frame)
      Shape             TexturedBox    86434 / 196608  px   43.96%  -> CONTRIBUTES
      ImageTexture      BaseTex            0 / 196608  px    0.00%  -> ABSENT
      (threshold: >= 98 changed px of 196608 to count as contributing)
   pair verdict: SEPARATED — correct variant contributes 86434 px; defective contributes 0 px — the differential catches this defect deterministically
   correction the check would emit:
      'BaseTex' (ImageTexture) is in the document but contributes no pixels: the texture is not reaching the surface. Check its containerField names a slot the material actually defines (baseTexture/emissiveTexture/normalTexture/... for PhysicalMaterial — NOT the default 'texture'), and that its url resolves.

── CASE 3. EnvironmentLight global (in a light rig)
   defect: x3d.py Bug 2 — the serializer drops global='true'
   components injected by reassert_profile: ["<component name='Lighting' level='2'/>", "<component name='Shape' level='5'/>"]
   note: Measured X_ITE 15.1.12 reality: an in-Transform EnvironmentLight is not applied even with global='true', so the correct variant's light may be reported absent too — a true 'in the document, not in the image' finding, but then the pair does NOT separate on `global` and the verdict below must say so. Case 3b covers the same defect class with a light whose scoping X_ITE does implement.
   variant: correct    (frame non-blank: True, stddev 13.5 — the blank gate passes this frame)
      EnvironmentLight  IBL                0 / 196608  px    0.00%  -> ABSENT
      Shape             LitBox             0 / 196608  px    0.00%  -> ABSENT
      Shape             Beacon          3809 / 196608  px    1.94%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   variant: defective  (frame non-blank: True, stddev 13.5 — the blank gate passes this frame)
      EnvironmentLight  IBL                0 / 196608  px    0.00%  -> ABSENT
      Shape             LitBox             0 / 196608  px    0.00%  -> ABSENT
      Shape             Beacon          3809 / 196608  px    1.94%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   pair verdict: NOT SEPARABLE (renderer) — the node is absent from the image even when authored correctly (0 px) — a true differential finding, but this renderer gives the pair nothing to separate on
   correction the check would emit:
      'IBL' (EnvironmentLight) is in the document but changes nothing in the render: the light is not lighting. For EnvironmentLight check that global='true' survived serialization (x3d.py drops it, Bug 2); otherwise check intensity, colour, and that the light is in scope for the geometry.

── CASE 3b. DirectionalLight global (same rig pattern)
   defect: the dropped-global defect class, on a light X_ITE scopes correctly
   components injected by reassert_profile: none
   variant: correct    (frame non-blank: True, stddev 55.8 — the blank gate passes this frame)
      DirectionalLight  Key            57633 / 196608  px   29.31%  -> CONTRIBUTES
      Shape             LitBox         53824 / 196608  px   27.38%  -> CONTRIBUTES
      Shape             Beacon          3809 / 196608  px    1.94%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   variant: defective  (frame non-blank: True, stddev 13.5 — the blank gate passes this frame)
      DirectionalLight  Key                0 / 196608  px    0.00%  -> ABSENT
      Shape             LitBox             0 / 196608  px    0.00%  -> ABSENT
      Shape             Beacon          3809 / 196608  px    1.94%  -> CONTRIBUTES
      (threshold: >= 98 changed px of 196608 to count as contributing)
   pair verdict: SEPARATED — correct variant contributes 57633 px; defective contributes 0 px — the differential catches this defect deterministically
   correction the check would emit:
      'Key' (DirectionalLight) is in the document but changes nothing in the render: the light is not lighting. For EnvironmentLight check that global='true' survived serialization (x3d.py drops it, Bug 2); otherwise check intensity, colour, and that the light is in scope for the geometry.

── ROOT-SCOPE NOTE (case 3 context)
   EnvironmentLight at Scene ROOT, global='true' vs dropped: frames differ by 0/196608 px
   -> at root scope the light's reach already covers the Scene, so Bug 2 has NO visual consequence there in this renderer.

── SUMMARY  (32 renders total)
   control clean, no defect missed. Where a pair did not separate, the reason is printed above and is a property of the renderer, not the check.
EXIT=0
```
