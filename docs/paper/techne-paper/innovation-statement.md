# Innovation Statement — Web3D 2026 AI + Web3D Innovation Competition

*Entrant: Alexander Hoffman. Generative AI (Anthropic's Claude) was used as a tool
under the author's direction; per ACM policy it is not an author. ~490 words.*

---

**Honest 3-D at machine speed.** A language model will build you an interactive
X3D scene in seconds — and that fluency is the danger. Its default failure mode is
confident, plausible invention: geometry that passes the X3D schema in full yet
renders mis-lit, mis-animated, or entirely blank, and a "reconstruction" that
looks authoritative while being unaccountable to any source. This entry shows that
a human–AI pair can author standards-conformant, interactive Web3D *fast* without
sacrificing correctness or honesty, and contributes the mechanism that makes that
possible.

**The working prototype** is a live, in-browser X_ITE archive
(https://euphememe.github.io/shasta-caves/): two Pleistocene fossil caves excavated
a century ago, rebuilt to scale in X3D 4.0 with physically based materials; an
HAnim LOA5 character pipeline; and a *documented* archive in which every survey
drawing and every excavated animal is a faithful vector trace of a cited,
public-domain original — no AI-generated imagery, no invented geometry. Each scene
labels, on screen, what is *documented* versus *interpretive*.

**The technical innovation** is **Technē**, a deterministic craft layer for Model
Context Protocol (MCP) servers (full paper enclosed). A schema certifies the
*shape* of a model's tool call but not whether the operation is *conventionally
correct* — the gap between *epistēmē* (the closed XSD) and *technē* (the contingent
craft the schema does not encode). Technē sits as a man-in-the-middle on the MCP
transport and makes three contributions: (1) it redirects schema-aligned argument
repair and craft validation onto the tool-call arguments a model emits *into* a
server, intercepted in transit; (2) it compiles a written catalogue of X3D
silent-failure modes into *prescriptive corrections* where the error message is the
fix ("use containerField='baseTexture'"), so the craft holds mechanically whether
or not the model understood it; and (3) its **occupation gate** executes a renderer
and inspects the pixels — *verify-by-render* — graduated so a glance precedes cheap
work and a human signature precedes expensive, irreversible rendering. It is built
on BAML, carries 147 passing unit tests, and is verified live end-to-end against the
production Web3D `x3d_mcp` server, which it caught real faults in.

**Why it advances AI + Web3D.** *Innovation:* nobody has pointed repair-and-validate
discipline at MCP tool-call arguments mid-flight, nor built a completion gate that
renders. *Technical excellence:* it directly strengthens the Working Group's own
`x3d_mcp` (three open upstream PRs). *AI integration:* the LLM is a fast, accountable
collaborator, not an oracle. *User experience:* the result is a navigable,
self-documenting 3-D archive a non-expert can explore in a browser. *Impact &
scalability:* the pattern is format-agnostic — wherever a flat MCP surface fronts a
craft a schema under-specifies, the same three moves compose, and the rule
catalogue is the only domain-specific asset.

**Links:** live site above · code https://github.com/EUPHEMEME/x3d_mcp (branches
`techne`, `potter-creek-cave`) · upstream PRs #9, #10, #11.
