// Codegen config. Generate the Python client to match x3d-mcp (Python), so the
// proxy can be one process (TECHNE_SPEC §4).
//
//   pip install baml-py
//   baml-cli generate           # produces ../baml_client/
//
generator techne {
  output_type "python/pydantic"
  output_dir "../"
  version "0.222.0"
}
