// A client is required to declare a BAML function. Technē's craft functions are
// "validation-shaped": at runtime the proxy calls `b.parse.ValidateX(json_str)`,
// which runs SAP repair + the @@assert/@@check rules on a provided string WITHOUT
// an LLM round-trip — preserving the governing determinism commitment
// (TECHNE_SPEC §0). This client therefore only needs to exist; it is not called
// on the validation path. Point it at any configured model if you ever want the
// LLM-backed repair mode.
client<llm> CustomFast {
  provider openai
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
  }
}
