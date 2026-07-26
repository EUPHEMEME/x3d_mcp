# EasyChair submission packet — Technē paper

**CFP:** https://easychair.org/cfp/web3d26 · Web3D 2026 (Doha)

## Which track / deadline
- **Full Papers track — deadline 25 June 2026, 11:00 PM PDT (extended).** ← this paper, tonight
  Notification 24 July · camera-ready 5 Aug. Limit: **9 pages exclusive of references** ✓ (body = 9pp, refs on p10).
- *(Separate)* **AI Tools / Web3D Innovation Competition — deadline 30 Aug 2026.** That's the
  `innovation-statement.md` + this paper enclosed. NOT tonight; ready when you want it.

## Upload
**PDF:** `docs/paper/techne-paper/techne.pdf` (583 KB, 10 pp = 9 content + refs). Anonymized build
("Anonymous Author(s)"); no name survives into the PDF. Keep the `anonymous` class option until camera-ready.

## EasyChair form fields

**Title:**
Technē: A Deterministic Craft Layer for Model Context Protocol Servers, Grounded in LLM-Authored X3D

**Authors (EasyChair metadata — these are NOT blind; reviewers see only the PDF):**
Alexander Hoffman · alex@euphe.me

**Abstract:**
A Model Context Protocol (MCP) server advertises its tools through a JSON Schema, so a language model can drive them by emitting typed tool calls. The schema is decidable and closed, yet it is the wrong success criterion: a model can emit calls that pass the schema in full and still produce a scene that renders mis-lit, mis-animated, or entirely blank. We name this the gap between epistēmē, the necessary formal structure a schema encodes, and technē, the contingent craft of making the artifact come out right that it does not. We present Technē, a deterministic craft layer that closes the gap for LLM-authored X3D over the Web3D x3d_mcp server. Technē is a man-in-the-middle MCP proxy and makes three contributions. First, it redirects Schema-Aligned-Parsing-style repair plus craft validation onto the tool-call arguments a model emits into a server, intercepted in transport — inverting the app-to-model seam that productised tools occupy. Second, it compiles a written catalogue of X3D silent-failure modes into named, prescriptive corrections where the error message is the fix, so the craft holds mechanically whether or not the model comprehended it. Third, its occupation gate executes a renderer and inspects the pixels — verify-by-render — graduated by irreversibility, something no assertion language can do. Beyond X3D correctness, the same move extends to honesty: an opt-in provenance gate compiles the documented/interpretive/generated convention into deterministic checks against an asset ledger, so a feature cannot be labelled documented without the source that documents it. The system is built on BAML, carries 105 passing unit tests, is measured against the bare server in a controlled comparison, and is verified live end-to-end against the production server.

**Keywords:**
Model Context Protocol; LLM tool use; agentic systems; Schema-Aligned Parsing; BAML; X3D; HAnim; Web3D; deterministic validation; prescriptive correction; verify-by-render; occupation gate; man-in-the-middle proxy; data provenance; documented vs interpretive

## Confirm before you click submit
1. **Track = Full Papers** (blind PDF, 25 June). If you actually mean the Aug-30 competition, that's a different
   submission and the non-blind statement applies.
2. **Camera-ready later:** drop `anonymous` from the `\documentclass` line and re-enable `\shortauthors` (both flagged in techne.tex).
3. Local build now uses **tectonic** (`tectonic techne.tex`) — LaTeX wasn't installed; tectonic fetches packages itself.
