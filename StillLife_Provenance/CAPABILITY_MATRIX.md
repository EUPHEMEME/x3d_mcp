# CAPABILITY_MATRIX — what X_ITE actually renders, measured
VERSION 1 · 2026-07-30 · probed against X_ITE **16.0.4** (jsdelivr `x_ite@latest`),
x3d.py **4.0.65.3/.4**, headless Chromium + swiftshader (the lookdev path).

**Method.** Every row is an A/B pair render at 360×280: identical scenes except the
one feature, pixel-diffed (`mad` = mean abs diff /255·3ch, `frac` = fraction of
pixels moved >8). Console captured per page — X_ITE *does* warn on unknown nodes
("Unknown node type …") but is **silent on unknown attributes** (e.g.
`transmission='1'` on PhysicalMaterial: no warning, no pixels). Renders are
deterministic (identical scenes re-navigated diff at mad 0.000), so mad 0.000 means
no-op, not noise. Probe code: session scratchpad `probes*.py`; renders + JSON in
`probe_out/`. All extension-node names verified against the browser's own
`getConcreteNodes()` enumeration (283 nodes under Full+components; the enumeration
is PROFILE-SCOPED — under bare Immersive you only see 163, and `createNode` lies
about availability accordingly).

## The two wrapper facts everything else depends on

1. **glTF material extensions need `<component name='X_ITE' level='1'/>` in
   `<head>`.** Profile `Full` alone does NOT enable them (still "Unknown node
   type"); Immersive + that one component statement does. **x3d.py REJECTS the
   name** (`X3DTypeError`, COMPONENTNAMECHOICES whitelist) → the component line
   must be injected post-serialization, same pass as the containerField fixes,
   and asserted.
2. **The known serializer hole is wider than pronk's.** x3d.py omits
   containerField not just on MetadataSet members and PhysicalMaterial texture
   slots but also on **EnvironmentLight** `diffuseTexture`/`specularTexture`
   (verified: two bare `<ComposedCubeMapTexture/>` children, indistinguishable).
   Inject + assert on every one of these slots.

## Matrix

| # | feature | node / field | x3d.py emits | X_ITE renders | evidence (A/B mad, frac) | use for |
|---|---------|--------------|--------------|---------------|--------------------------|---------|
| 1 | X3D 4.1 version | `X3D version='4.1'` | yes (4.1 DTD) | accepted, **zero effect** | red box 4.0 vs 4.1: mad 0.000, no console warnings | Nothing. No 4.1-only renderable node found. Stay on 4.0. |
| 2 | PBR base texture | `PhysicalMaterial.baseTexture` | yes, **no containerField** | **yes** | mad 18.8, frac 0.34 | albedo everywhere |
| 3 | **Normal maps** | `PhysicalMaterial.normalTexture` (+`normalScale`) | yes, no cF | **yes** | mad 7.3, frac 0.13; visually: banded shading, split highlight | damask weave, pewter hammer marks, bread crust — the surface-relief lever, it works |
| 4 | Baked AO | `PhysicalMaterial.occlusionTexture` | yes, no cF | **yes — but ONLY against ambient/IBL** | direct-light-only scene: mad **0.000**; same + EnvironmentLight: mad 43.2, frac 0.18 | contact shadows that actually draw — REQUIRES an EnvironmentLight (or ambient term) in scene, else silent no-op |
| 5 | Rough/metal maps | `PhysicalMaterial.metallicRoughnessTexture` (G=rough, B=metal) | yes, no cF | **yes** | mad 17.3, frac 0.27; matte/gloss stripes visible | worn silver, smudged glass, waxed wood |
| 6 | Emissive texture | `PhysicalMaterial.emissiveTexture` | yes, no cF | **yes — multiplied by emissiveColor** | with default emissiveColor 0 0 0: mad **0.000**; with 1 1 1: mad 57.6 | candle flames, lit windows. MUST set emissiveColor≠black or it is a hard no-op |
| 7 | Alpha transparency | `PhysicalMaterial.transparency` | yes | **yes** (plain alpha blend) | mad 15.9; backdrop reads through, no refraction/fresnel | the only see-through there is; cellophane not glass |
| 8 | transmission attr | `PhysicalMaterial transmission='1'` | n/a (not a field) | **NO — silently ignored, not even a console warning** | mad 0.000, console clean | the trap this project was warned about, live instance |
| 9 | Transmission / IOR / Volume glass | `TransmissionMaterialExtension`, `IORMaterialExtension`, `VolumeMaterialExtension` in `PhysicalMaterial.extensions` | **no class** → raw XML | **NO — parse clean under X_ITE component, zero pixels** | 3 setups (geometry backdrop, IBL only, IBL+backdrop): all mad 0.000 | **glass is a dead end. Design around:** transparency + baked highlight/reflection geometry |
| 10 | **IBL, specular side** | `EnvironmentLight.specularTexture` ← `ComposedCubeMapTexture` (needs component `CubeMapTexturing:3`) | yes (component OK; slot needs cF inject) | **YES** | mirror sphere: mad 42.2; visually a clean cubemap reflection | reflections on silver/glass/glaze — the biggest "looks lit" lever available |
| 11 | **IBL, diffuse side** | same `specularTexture` — X_ITE derives irradiance from it | (same) | **YES** | matte sphere under specular-only cubemap: mad 24.7, smooth colored gradient | soft directional ambience for the whole tableau; one cubemap feeds both |
| 12 | IBL via diffuseTexture | `EnvironmentLight.diffuseTexture` | yes, no cF | **NO** | matte sphere: mad 0.000 vs color-only light | dead slot, don't bother |
| 13 | IBL via SH | `EnvironmentLight.diffuseCoefficients` | yes | **NO** | warm SH coefficients: mad 0.000, no tint | dead field, don't bother |
| 14 | Env light, flat | `EnvironmentLight color/intensity` (no textures) | yes | yes | on/off: mad 88.5 | ambient fill; also what unlocks row 4 |
| 15 | **Sheen** | `SheenMaterialExtension sheenColor/sheenRoughness` | **no class** → raw XML | **YES** | mad 4.3, frac 0.13; visually a true velvet rim | tablecloth, velvet, bread — exactly the cloth response wanted |
| 16 | Iridescence | `IridescenceMaterialExtension` | no class → raw XML | **yes** | mad 3.3, frac 0.20; hue shifts + green rim under IBL | mother-of-pearl, oil film, roemer glass tint |
| 17 | Clearcoat | `ClearcoatMaterialExtension` | no class → raw XML | yes, subtle | mad 0.45, frac 0.014; sharp secondary highlight visible | glazed ceramic, varnished wood |
| 18 | Emissive strength | `EmissiveStrengthMaterialExtension` | no class → raw XML | yes | mad 30.2 | HDR-ish glow without blowing baseColor |
| 19 | Specular ext | `SpecularMaterialExtension specular/specularColor` | no class → raw XML | yes (small measured effect) | killing specular: mad 0.58, frac 0.0016 — the highlight area only | tuning dielectric highlight strength; weak lever, verify visually per use |
| 20 | Texture projector | `TextureProjector` (component `TextureProjection:2`) | **yes** (class + component both emit) | **YES** | mad 12.3, frac 0.61; projected pattern visible | slide-projector light: window-light gobos, dappled light — cheap "painted light" |
| 21 | Anisotropic filtering | `TextureProperties anisotropicDegree` | yes | **yes** | 1 vs 16 at grazing: mad 11.9; line detail holds visibly farther | tablecloth/board textures at still-life camera angles stop shimmering |
| 22 | Texture tiling | `TextureTransform scale` | yes | yes | mad 46.5 | weave/grain density without bigger images |
| 23 | ClipPlane | `ClipPlane` | yes | yes | mad 10.0, frac 0.12 | cut-aways; sliced cheese/fruit interiors |
| 24 | LocalFog | `LocalFog` | yes | yes | mad 27.7 | atmospheric depth behind the tableau |
| 25 | Billboard | `Billboard axisOfRotation='0 0 0'` | yes | yes | edge-on panel vs facing: mad 20.4 | camera-facing cards (flame sprites) |
| 26 | LOD | `LOD range` | yes | yes | near/far child switch: mad 83.0 | not pictorial; harness economy only |

Not probed for pixels (exist per node enumeration): `DiffuseTransmissionMaterialExtension`,
`DispersionMaterialExtension`, `VolumeScatterMaterialExtension` (their parents in row 9
are no-ops — assume dead until proven), `AnisotropyMaterialExtension` (specular
anisotropy — could matter for pewter; probe before relying), `GeneratedCubeMapTexture`,
`ImageCubeMapTexture`, `GaussianSplats`, `BlendMode`, `DepthMode`.

## What this means for the three pictures

- **Light the tableaux with one authored cubemap** on `EnvironmentLight.specularTexture`
  (component `CubeMapTexturing:3`): it supplies reflections AND soft diffuse ambience
  from a single asset, and it is what makes occlusionTexture (baked contact shadow)
  fire at all. Keep the DirectionalLight as key; the env light replaces the dead flat fill.
- **Cloth = normalTexture + SheenMaterialExtension.** Both verified. This is damask,
  velvet, the letter-rack straps.
- **Glass/silver = mirror-side IBL + transparency + baked highlights.** Transmission
  refraction does not exist here; stop reaching for it.
- **Injection pass grows:** containerField on MetadataSet values, PhysicalMaterial
  texture slots, EnvironmentLight texture slots, ComposedCubeMapTexture face slots
  (`frontTexture`… — **verified omitted too**, and the serializer reorders the
  children alphabetically, so without injected containerFields the faces come out
  scrambled), PLUS the
  `<component name='X_ITE' level='1'/>` head line and raw-XML extension nodes.
  Assert every one after serialization; X_ITE will not warn you about a dropped attribute.
