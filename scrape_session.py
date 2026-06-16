#!/usr/bin/env python3
"""Scrape a Claude Code session JSONL transcript into the project's two standard
local records:

  sessions/<name>.json   -- the raw JSONL transcript, copied verbatim
  sessions/<name>.md      -- a readable markdown render (👤 User / 🤖 Assistant /
                             🔧 tool calls / > 🔧 result blockquotes)

Both live under sessions/ which is gitignored (local record, not for the shared
repo). Re-run to refresh after more conversation.

Usage:  python scrape_session.py [SESSION_JSONL] [OUT_NAME]
Defaults to the newest *.jsonl in this project's Claude transcript dir and the
name 'potter_creek_cave_session'.
"""
import json
import os
import sys
import glob
import shutil

PROJ_DIR = os.path.expanduser(
    "~/.claude/projects/-Users-alexander-x3d-mcp")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")


def newest_jsonl():
    cands = glob.glob(os.path.join(PROJ_DIR, "*.jsonl"))
    if not cands:
        sys.exit(f"no .jsonl transcripts in {PROJ_DIR}")
    return max(cands, key=os.path.getmtime)


def as_text(content):
    """Flatten a message 'content' (str or list of blocks) for the .md render."""
    if isinstance(content, str):
        return [("text", content)]
    out = []
    for b in content or []:
        if not isinstance(b, dict):
            out.append(("text", str(b)))
            continue
        t = b.get("type")
        if t == "text":
            out.append(("text", b.get("text", "")))
        elif t == "tool_use":
            out.append(("tool_use", b))
        elif t == "tool_result":
            out.append(("tool_result", b))
        elif t == "thinking":
            out.append(("thinking", b.get("thinking", "")))
        elif t == "image":
            out.append(("text", "_(image)_"))
    return out


def tool_label(b):
    name = b.get("name", "tool")
    inp = b.get("input", {}) or {}
    desc = inp.get("description") or inp.get("file_path") or inp.get("query") \
        or inp.get("command") or inp.get("path") or inp.get("skill")
    if desc:
        desc = str(desc).splitlines()[0][:120]
        return f"🔧 **{name} — {desc}**"
    return f"🔧 **{name}**"


def result_text(b):
    c = b.get("content", "")
    if isinstance(c, list):
        parts = []
        for x in c:
            if isinstance(x, dict):
                if x.get("type") == "text":
                    parts.append(x.get("text", ""))
                elif x.get("type") == "image":
                    parts.append("_(image)_")
            else:
                parts.append(str(x))
        c = "\n".join(parts)
    c = str(c).strip()
    if len(c) > 4000:
        c = c[:4000] + "\n… (truncated)"
    return c


def render(jsonl_path):
    blocks = [
        "# Claude Code session transcript",
        "",
        f"_Source: {jsonl_path}_",
        "",
        "---",
        "",
    ]
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            typ = rec.get("type")
            if typ not in ("user", "assistant"):
                continue
            msg = rec.get("message", {})
            for kind, payload in as_text(msg.get("content")):
                if kind == "text":
                    if not str(payload).strip():
                        continue
                    head = "## 👤 User" if typ == "user" else "## 🤖 Assistant"
                    blocks += [head, "", str(payload).rstrip(), "", "---", ""]
                elif kind == "thinking":
                    if str(payload).strip():
                        blocks += ["## 🤖 Assistant",
                                   "", "> 💭 _(thinking)_ " +
                                   str(payload).strip()[:1500],
                                   "", "---", ""]
                elif kind == "tool_use":
                    blocks += ["## 🤖 Assistant", "",
                               tool_label(payload), "", "---", ""]
                elif kind == "tool_result":
                    blocks += ["> 🔧 result: " +
                               result_text(payload).replace("\n", "\n> "),
                               "", "---", ""]
    return "\n".join(blocks) + "\n"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else newest_jsonl()
    name = sys.argv[2] if len(sys.argv) > 2 else "potter_creek_cave_session"
    os.makedirs(OUT_DIR, exist_ok=True)
    json_out = os.path.join(OUT_DIR, name + ".json")
    md_out = os.path.join(OUT_DIR, name + ".md")
    shutil.copyfile(src, json_out)              # verbatim JSONL transcript
    with open(md_out, "w") as f:
        f.write(render(src))
    n_lines = sum(1 for _ in open(src))
    print(f"scraped {src}\n  -> {json_out} ({os.path.getsize(json_out)//1024} KB, "
          f"{n_lines} records)\n  -> {md_out} ({os.path.getsize(md_out)//1024} KB)")


if __name__ == "__main__":
    main()
