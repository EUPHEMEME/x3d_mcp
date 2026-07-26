# EasyChair submission packet — Technē paper

**CFP:** https://easychair.org/cfp/web3d26 · Web3D 2026 (Doha)

## Which track / deadline
- **Full Papers track — deadline 25 June 2026, 11:00 PM PDT (extended).** ← this paper.
  Notification 24 July · camera-ready 5 Aug. Limit: **9 pages exclusive of references** ✓ (body ends on p9; refs spill p9→p10 — verified).
- *(Separate)* **AI Tools / Web3D Innovation Competition — deadline 30 Aug 2026.** That's the
  `innovation-statement.md` + this paper enclosed. NOT tonight; ready when you want it.

## Upload
**PDF:** `docs/paper/techne-paper/techne-v2.pdf` (560 KB, 9 pp + refs). Anonymized build
("Anonymous Author(s)"); no name survives into the PDF. Keep the `anonymous` class option until camera-ready.

## EasyChair form fields

**Title:**
Technē: A Deterministic Craft Layer for Model Context Protocol Servers, Grounded in LLM-Authored X3D

**Authors (EasyChair metadata — NOT blind; reviewers see only the PDF). EasyChair wants a per-author record:**
- First name: **Alexander** · Last name: **Hoffman**
- Email: **alex@euphe.me**
- Affiliation: **Independent Researcher** · Country: **USA**
- Tick **corresponding author**

**Abstract:**
When a language model builds 3D content by calling tools through the Model Context Protocol (MCP), the JSON Schema ensures each call is well-formed — but not that the result will render correctly. A texture placed in the wrong slot vanishes. A humanoid skeleton routed to the wrong parent field is invisible. The schema passes; the pixels fail. We present Technē, a deterministic MCP proxy for the Web3D x3d_mcp server that catches these failures. Sitting between the model and the real server, Technē intercepts each tool call and (1) repairs sloppy arguments using Postel-style coercion, (2) checks a catalog of documented X3D silent-failure modes, returning prescriptive corrections that name the exact fix, and (3) renders the scene and checks for blank frames — a test no schema validator can perform. An opt-in provenance gate extends the same approach to content honesty. On correct input Technē is invisible. The system runs no LLM in the enforcement loop, carries 147 passing unit tests, and is measured against the bare server in a controlled comparison.

**Keywords:**
Model Context Protocol; LLM tool use; agentic systems; Schema-Aligned Parsing; BAML; X3D; HAnim; Web3D; deterministic validation; prescriptive correction; verify-by-render; occupation gate; man-in-the-middle proxy; data provenance; documented vs interpretive

## EasyChair will also ask (stage these)
- **Topics:** EasyChair shows a checkbox list of the conference's topic areas — separate from the free-text keywords above, which won't tick them. Pick the fits: AI/LLMs, authoring tools, X3D / HAnim, validation, Web3D standards.
- **Declarations / conflicts of interest:** you'll likely confirm the work is original and not under concurrent review, and declare any conflict with program-committee members. You have none unless you personally know a PC member.

## Confirm before you click submit
1. **Track = Full Papers** (blind PDF, 25 June). If you actually mean the Aug-30 competition, that's a different
   submission and the non-blind statement applies.
2. **Camera-ready later:** drop `anonymous` from the `\documentclass` line and re-enable `\shortauthors` (both flagged in techne.tex).
3. Local build now uses **tectonic** (`tectonic techne-v2.tex`) — LaTeX wasn't installed; tectonic fetches packages itself.
