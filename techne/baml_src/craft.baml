// Technē craft-rules — the CANONICAL declaration of the X3D silent-failure modes
// (TECHNE_SPEC §3). The deterministic engine in techne/craft.py mirrors these;
// this file is the source of truth and the path to BAML SAP repair.
//
// Source of the rules: docs/x3dpy-bug-report.md and TECHNE_SPEC §3.
// Every assertion is NAMED; the proxy maps the name -> prescriptive correction
// (techne/rules.py CATALOG), so a failure says "use containerField='baseTexture'",
// not bare "invalid".
//
// CRITICAL (TECHNE_SPEC §1 gotcha): only BLOCK-LEVEL @@assert / @@check (double @)
// actually fire. Field-level single-@ is silently ignored at runtime. Everything
// below is @@.  @@assert == HARD (blocks, throws BamlValidationError); @@check ==
// SOFT (advisory, non-blocking).


// --- Mode 1: dropped containerField (Bug 1) --------------------------------
class TextureAttachment {
  parent_type     string   // e.g. "PhysicalMaterial"
  texture_type    string   // e.g. "ImageTexture"
  container_field string   // THE craft-critical field x3d.py drops
  url             string

  // HARD: containerField must be present; dropping it routes the texture into
  // ImageTexture's default 'texture' slot, which PBR materials do not define.
  @@assert(container_field_present, {{ this.container_field|length > 0 }})

  // HARD: the slot must be a legal texture slot for a PBR material. (The full
  // per-material slot table lives in techne/rules.py MATERIAL_TEXTURE_SLOTS; the
  // proxy enforces the parent-specific subset.)
  @@assert(container_field_correct, {{
       this.container_field == "baseTexture"
    or this.container_field == "emissiveTexture"
    or this.container_field == "normalTexture"
    or this.container_field == "occlusionTexture"
    or this.container_field == "metallicRoughnessTexture"
  }})

  // SOFT: url should resolve to a known image extension.
  @@check(texture_url_image_ext, {{
       this.url|lower is endingwith(".png")
    or this.url|lower is endingwith(".jpg")
    or this.url|lower is endingwith(".jpeg")
    or this.url|lower is endingwith(".webp")
  }})
}

function ValidateTextureAttachment(raw: TextureAttachment) -> TextureAttachment {
  client CustomFast
  prompt #"
    Return the texture attachment unchanged. {{ ctx.output_format }}
    {{ raw }}
  "#
}


// --- Mode 2: EnvironmentLight.global (Bug 2) -------------------------------
class EnvironmentLightArgs {
  // True when 'global' was written explicitly. x3d.py defaults global to True and
  // then OMITS it; a spec-default reader parses the omission as false and IBL
  // silently dies. So: it must be explicitly present.
  global_present  bool

  @@assert(envlight_global_set, {{ this.global_present }})
}

function ValidateEnvironmentLight(raw: EnvironmentLightArgs) -> EnvironmentLightArgs {
  client CustomFast
  prompt #"Return unchanged. {{ ctx.output_format }} {{ raw }}"#
}


// --- Mode 3: interpolator key / keyValue parity ----------------------------
class InterpolatorArgs {
  node_type           string
  key_count           int    // number of key fractions
  key_value_count     int    // number of flattened keyValue components
  components_per_key  int    // 4 (Orientation), 3 (Position/Color/Normal), 1 (Scalar)

  // HARD: keyValue length must equal key length x components-per-key, or the
  // animation is silently corrupted.
  @@assert(interp_lengths_match, {{
    this.key_value_count == this.key_count * this.components_per_key
  }})
}

function ValidateInterpolator(raw: InterpolatorArgs) -> InterpolatorArgs {
  client CustomFast
  prompt #"Return unchanged. {{ ctx.output_format }} {{ raw }}"#
}


// --- Mode 4: USE-after-DEF (single-call form) ------------------------------
class UseRef {
  use_name        string
  // True when the referenced DEF exists in scope (the proxy supplies this from
  // its cross-call scene state; the single-call form checks the current payload).
  def_in_scope    bool

  @@assert(use_after_def, {{ this.def_in_scope }})
}

function ValidateUseRef(raw: UseRef) -> UseRef {
  client CustomFast
  prompt #"Return unchanged. {{ ctx.output_format }} {{ raw }}"#
}
