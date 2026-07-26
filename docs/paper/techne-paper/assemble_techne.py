#!/usr/bin/env python3
"""Assemble the Technē conference paper (acmart sigconf) from the drafting
workflow's JSON (/tmp/techne_paper.json: {sections:[{key,sec,latex}], weave:{...}}).

Preamble, bibliography, figures (2 TikZ + 1 reused PNG), and the ACM-compliant
Use-of-Generative-AI statement live here (static, hand-verified); the section
bodies + the editor's abstract/intro/conclusion come from the workflow.
"""
import json
import re

DATA = json.load(open("/tmp/techne_paper.json"))
secs = {s["key"]: s["latex"] for s in DATA["sections"]}
w = DATA["weave"]

ORDER = ["background", "gap", "arch", "point2", "point3", "eval", "discussion"]
title = w.get("title", "Techn\\=e: A Deterministic Craft Layer for MCP Servers").strip()


def strip_fences(s):
    s = (s or "").strip()
    s = re.sub(r'^```(?:latex|tex)?\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    return s.strip()


_PROT = re.compile(
    r'(\\(?:ref|label|cite|includegraphics|url|input|Cref|cref|ccsdesc)\{[^}]*\}'
    r'|\\fig\{[^}]*\})')


def latex_clean(s):
    s = s.replace(r'\&amp;', r'\&').replace('&amp;', r'\&')
    s = s.replace('&lt;', r'\textless{}').replace('&gt;', r'\textgreater{}')
    out, parts = [], _PROT.split(s)
    for i, p in enumerate(parts):
        out.append(p if i % 2 else re.sub(r'(?<!\\)_', r'\\_', p))
    return ''.join(out)


LABELS = {"background": "sec:related", "gap": "sec:gap", "arch": "sec:arch",
          "point2": "sec:point2", "point3": "sec:point3", "eval": "sec:eval",
          "discussion": "sec:discussion"}


def ensure_label(latex, key):
    lab = LABELS[key]
    if "\\label{%s}" % lab in latex:
        return latex
    return re.sub(r'(\\section\{[^}]*\})', r'\1\\label{%s}' % lab, latex, count=1)


body = "\n\n".join(latex_clean(ensure_label(strip_fences(secs[k]), k))
                   for k in ORDER if k in secs)

PREAMBLE = r"""\documentclass[sigconf,nonacm,screen]{acmart}
\settopmatter{printacmref=false}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta}
\usepackage{booktabs}
\usepackage{balance}

\begin{document}

\title{%s}

\author{Alexander Hoffman}
\affiliation{%%
  \institution{Independent Researcher}
  \country{USA}}
\email{alex@euphe.me}

\renewcommand{\shortauthors}{Hoffman}

\begin{abstract}
%s
\end{abstract}

%s
\keywords{%s}

\maketitle
""" % (title, latex_clean(strip_fences(w["abstract"])),
       strip_fences(w.get("ccs", "")), w.get("keywords", "X3D, Model Context "
       "Protocol, large language models, generative 3D, validation, provenance"))

# --- figures ---------------------------------------------------------------
FIG_ARCH = r"""
\begin{figure}[t]\centering
\begin{tikzpicture}[font=\footnotesize, >=Stealth, node distance=10mm,
  box/.style={draw, rounded corners, align=center, inner sep=4pt, minimum height=8mm}]
  \node[box] (model) {Model\\(draftsman)};
  \node[box, right=14mm of model, fill=black!5, align=left] (techne)
    {\textbf{Techn\=e proxy}\\[1pt]
     1.\ SAP repair\\
     2.\ craft \texttt{@@assert}/\texttt{@@check}\\
     3.\ occupation gate};
  \node[box, right=14mm of techne] (mcp) {x3d-mcp\\(real server)};
  \draw[->] (model.12) -- node[above,font=\scriptsize]{call(args)} (techne.168);
  \draw[->] (techne.12) -- node[above,font=\scriptsize]{repaired} (mcp.168);
  \draw[<-] (model.348) -- node[below,font=\scriptsize]{result / correction} (techne.192);
  \draw[<-] (techne.348) -- node[below,font=\scriptsize]{result} (mcp.192);
\end{tikzpicture}
\caption{Techn\=e as an MCP man-in-the-middle. Each \texttt{tools/call} is
repaired (Postel-style), validated against the craft rules, and either forwarded
with rewritten arguments or blocked with a prescriptive correction; the
completion gate renders and inspects the result. Opt-in per tool.}
\label{fig:arch}
\end{figure}
"""

FIG_RENDERER = r"""
\begin{figure}[t]\centering
\includegraphics[width=\columnwidth]{../figures/x3dom_vs_xite.png}
\caption{The renderer is a correctness property, not an aesthetic one. The same
scene under headless software WebGL: X3DOM (left) draws nothing for HAnim and X3D
4.0 \texttt{PhysicalMaterial}; \mbox{X\_ITE} (right) renders both. An X3DOM-based
completion gate would inspect a blank and pass it.}
\label{fig:renderer}
\end{figure}
"""

FIG_GATE = r"""
\begin{figure}[t]\centering
\begin{tikzpicture}[font=\footnotesize, >=Stealth,
  box/.style={draw, rounded corners, align=left, inner sep=5pt, text width=0.84\columnwidth}]
  \node[box] (cheap) {\textbf{Cheap gate} — automatic, soft.\\
     Fast preview render $\rightarrow$ ``looks non-blank?'' Advisory warning.};
  \node[box, below=7mm of cheap, fill=black!5] (exp)
    {\textbf{Expensive gate} — hard.\\
     Before the irreversible offline photoreal render: surface the preview,
     \emph{stop}, and await the human architect's sign-off. The draftsman never
     pours concrete on its own authority.};
  \draw[->] (cheap) -- node[right,font=\scriptsize]{irreversibility $\uparrow$} (exp);
\end{tikzpicture}
\caption{The occupation gate is graduated by irreversibility: a soft check before
cheap reversible work, a hard human sign-off before expensive irreversible work.}
\label{fig:gate}
\end{figure}
"""

INTRO = latex_clean(strip_fences(w["intro_latex"]))
CONC = latex_clean(strip_fences(w["conclusion_latex"]))

AI_STMT = r"""
\section*{Use of generative AI}
Anthropic's Claude (Claude Code) was used as a tool throughout this work---for
software implementation, validation, render automation, and drafting---under the
human author's direction. In keeping with the ACM Policy on Authorship, the
generative AI is not credited as an author: the human author conceived the work,
designed the system, made every substantive decision, and is solely responsible
for the content. This statement discloses its use as required.
"""

BIB = r"""
\bibliographystyle{ACM-Reference-Format}
\begin{thebibliography}{00}
\providecommand{\doi}[1]{\href{https://doi.org/#1}{doi:#1}}

\bibitem{mcp} Anthropic. 2024. \emph{Model Context Protocol Specification}.
\url{https://modelcontextprotocol.io}

\bibitem{baml} BoundaryML. 2024. \emph{BAML and Schema-Aligned Parsing}.
\url{https://github.com/BoundaryML/baml}

\bibitem{postel} J.~Postel. 1980. \emph{Transmission Control Protocol}. RFC~761.
(The robustness principle: be conservative in what you do, liberal in what you
accept.)

\bibitem{x3d4} ISO/IEC 19775-1:2023. \emph{Extensible 3D (X3D) Part~1:
Architecture and base components} (X3D~4.0). Web3D Consortium / ISO.

\bibitem{hanim} ISO/IEC 19774:2019. \emph{Humanoid Animation (HAnim)}.

\bibitem{x3duom} Web3D Consortium. \emph{X3D Unified Object Model (X3DUOM)}.
\url{https://www.web3d.org/specifications/X3DUOM.html}

\bibitem{xite} H.~Seelig. \emph{X\_ITE: An X3D Browser for the Web}.
\url{https://create3000.github.io/x_ite/}

\bibitem{x3dom} J.~Behr, P.~Eschler, Y.~Jung, and M.~Z\"ollner. 2009. X3DOM: a
DOM-based HTML5/X3D integration model. In \emph{Proc.\ 14th Int.\ ACM Conf.\ on
3D Web Technology (Web3D~'09)}. \doi{10.1145/1559764.1559784}

\bibitem{gltf} Khronos Group. \emph{glTF 2.0 Specification} (metallic--roughness
physically based rendering).

\bibitem{x3dpy} Web3D Consortium. \emph{x3d.py: the X3D Python (SAI) package}.
\url{https://pypi.org/project/x3d/}

\bibitem{castle} M.~Kambur\-elis. \emph{Castle Game Engine / Castle Model Viewer}.
\url{https://castle-engine.io/}

\bibitem{playwright} Microsoft. \emph{Playwright}. \url{https://playwright.dev/}

\bibitem{prompteng} \emph{Prompt Engineering for X3D Object Creation with Large
Language Models}. In \emph{Proc.\ ACM Int.\ Conf.\ on 3D Web Technology
(Web3D~'25)}. [Exact author/page details to be completed.]

\bibitem{audiocaption} N.~Polys and S.~M.~Wasi. 2023. Increasing Web3D
Accessibility with Audio Captioning. In \emph{Proc.\ 28th Int.\ ACM Conf.\ on 3D
Web Technology (Web3D~'23)}, Article~6, 1--10. \doi{10.1145/3611314.3615902}

\bibitem{blackboard} H.~P.~Nii. 1986. Blackboard Systems. \emph{AI Magazine}
7,~2 (1986), 38--53.

\bibitem{jsonschema} \emph{JSON Schema}. \url{https://json-schema.org/}

\bibitem{x3dexamples} Web3D Consortium. \emph{X3D Examples Archives}.
\url{https://www.web3d.org/x3d/content/examples/}

\end{thebibliography}
"""

doc = (PREAMBLE + "\n" + FIG_ARCH + "\n" + INTRO + "\n\n"
       + FIG_RENDERER + "\n" + body + "\n\n" + FIG_GATE + "\n"
       + CONC + "\n" + AI_STMT + "\n\\balance\n" + BIB + "\n\\end{document}\n")
open("techne.tex", "w").write(doc)
print(f"wrote techne.tex ({len(doc)} chars; sections: "
      f"{['intro'] + [k for k in ORDER if k in secs] + ['conclusion']})")
for c in w.get("coherence_fixes", []):
    print(f"  fix [{c.get('section')}]: {str(c.get('issue'))[:80]}")
