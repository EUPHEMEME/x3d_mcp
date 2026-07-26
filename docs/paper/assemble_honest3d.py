#!/usr/bin/env python3
"""Assemble the long-form vision paper honest-3d.tex from the drafting workflow's
JSON output (/tmp/honest3d.json: {sections:[{key,latex}], weave:{...}}).

Preamble + the full bibliography live here (static, hand-verified); the section
bodies + the editor's vision/abstract/conclusion come from the workflow.
"""
import json
import re

DATA = json.load(open("/tmp/honest3d.json"))
secs = {s["key"]: s["latex"] for s in DATA["sections"]}
w = DATA["weave"]

ORDER = ["provenance", "toolchain", "characters", "caves", "roadmap", "ethics"]
title = w.get("final_title", "Honest 3-D at Machine Speed").strip()
abstract = w["abstract"].strip()
vision = w["vision_section_latex"].strip()
conclusion = w["conclusion_section_latex"].strip()

# clean the title separately (no underscores expected; keep simple)
title = title.replace("&amp;", "\\&")


def strip_fences(s):
    s = s.strip()
    s = re.sub(r'^```(?:latex|tex)?\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    return s.strip()


# protect filenames / ref-keys (need literal '_'); escape bare '_' everywhere else
_PROT = re.compile(
    r'(\\(?:ref|label|cite|includegraphics|url|input)\{[^}]*\}|\\fig\{[^}]*\})')


def latex_clean(s):
    # stray HTML entities some drafters emitted inside LaTeX
    s = s.replace(r'\&amp;', r'\&').replace('&amp;', r'\&')
    s = s.replace('&lt;', r'\textless{}').replace('&gt;', r'\textgreater{}')
    # escape bare underscores, but not inside protected command arguments
    out, parts = [], _PROT.split(s)
    for i, p in enumerate(parts):
        out.append(p if i % 2 else re.sub(r'(?<!\\)_', r'\\_', p))
    return ''.join(out)


LABELS = {"provenance": "sec:provenance", "toolchain": "sec:toolchain",
          "characters": "sec:characters", "caves": "sec:caves",
          "roadmap": "sec:future", "ethics": "sec:ethics"}


def ensure_label(latex, key):
    lab = LABELS[key]
    if "\\label{%s}" % lab in latex:
        return latex
    return re.sub(r'(\\section\{[^}]*\})', r'\1\\label{%s}' % lab, latex, count=1)


body = "\n\n".join(latex_clean(ensure_label(strip_fences(secs[k]), k))
                   for k in ORDER if k in secs)

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{xurl}
\usepackage[htt]{hyphenat}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{parskip}
\setlength{\emergencystretch}{3em}
\hypersetup{colorlinks=true, linkcolor=blue!45!black,
  urlcolor=blue!45!black, citecolor=blue!45!black}
\graphicspath{{figures/}}
\newcommand{\fig}[3]{\begin{figure}[ht]\centering
  \includegraphics[width=#2\linewidth]{#1}
  \caption{#3}\label{fig:#1}\end{figure}}
\newcommand{\xite}{X\_ITE}

\title{\textbf{%s}}
\author{Alexander Hoffman \and Claude (Anthropic Claude Code)\\[2pt]
  \small\textit{Draft --- collaborative authorship}}
\date{\today}

\begin{document}
\maketitle
\begin{abstract}
%s
\end{abstract}
""" % (title, latex_clean(abstract))

BIB = r"""
\begin{thebibliography}{99}
\small
\bibitem{x3d4} ISO/IEC 19775-1:2023, \emph{X3D Architecture and base components}
(X3D 4.0). Web3D Consortium / ISO.
\bibitem{hanim} ISO/IEC 19774-1:2019, \emph{Humanoid Animation (HAnim)
architecture}.
\bibitem{loa5draft} Web3D Consortium, \emph{X3D version 4 draft: ISO/IEC 19774
Humanoid Animation}, including the draft Level of Articulation~5 (LOA5).
\url{https://www.web3d.org/specifications/X3Dv4Draft/ISO-IEC19774/}
\bibitem{allbones} Web3D Consortium, \emph{AllBonesLOA5Skeletons} example model
(HumanoidAnimation/Bones).
\url{https://www.web3d.org/x3d/content/examples/HumanoidAnimation/Bones/}
\bibitem{x3duom} Web3D Consortium, \emph{X3D Unified Object Model (X3DUOM)}.
\bibitem{xite} H.~Seelig, \emph{\xite{} X3D Browser}, v15.1.4.
\url{https://create3000.github.io/x_ite/}
\bibitem{x3dom} J.~Behr et al., \emph{X3DOM} (\texttt{x3dom.org/release}).
\url{https://www.x3dom.org/}
\bibitem{x3dpy} Web3D Consortium, \emph{x3d.py --- X3D Python SAI package},
v4.0.65.3. \url{https://pypi.org/project/x3d/}
\bibitem{x3dtox3dom} Web3D Consortium, \emph{X3dToX3dom.xslt} stylesheet.
\url{https://www.web3d.org/x3d/stylesheets/X3dToX3dom.xslt}
\bibitem{saxon} Saxonica, \emph{Saxon-HE} (XSLT~2.0 processor), v9.9.1-8.
\bibitem{castle} M.~Kambur\-elis, \emph{Castle Model Viewer} (Castle Game Engine).
\url{https://castle-engine.io/castle-model-viewer}
\bibitem{netbeans} Web3D Consortium / Naval Postgraduate School, \emph{X3D-Edit}
(Apache NetBeans plugin). \url{https://savage.nps.edu/X3D-Edit/}
\bibitem{gltf} Khronos Group, \emph{glTF 2.0 Specification} (metallic-roughness
PBR material model).
\bibitem{mcp} Anthropic, \emph{Model Context Protocol specification}.
\url{https://modelcontextprotocol.io}
\bibitem{mflux} Black Forest Labs, \emph{FLUX.1} text-to-image model, run locally
on Apple MLX via \emph{mflux}. \url{https://github.com/filipstrand/mflux}
\bibitem{sinclair03} W.~J.~Sinclair (1903) A preliminary account of the
exploration of the Potter Creek Cave. \emph{Science} 17(435):708--712.
\bibitem{sinclair04} W.~J.~Sinclair (1904) The exploration of the Potter Creek
Cave. \emph{Univ. Calif. Publ. Amer. Arch. Ethn.} 2(1):1--27.
\bibitem{sinclair05} W.~J.~Sinclair (1905) New Mammalia from the Quaternary caves
of California. \emph{Univ. Calif. Publ. Geol.} 4:145--161.
\bibitem{sf04} W.~J.~Sinclair \& E.~L.~Furlong (1904) \emph{Euceratherium}, a new
ungulate from the Quaternary caves of California. \emph{Univ. Calif. Publ. Bull.
Dept. Geol.} 3(20):411--418.
\bibitem{furlong06} E.~L.~Furlong (1906) The exploration of Samwel Cave.
\emph{Am. J. Sci.} 22(129):235--247.
\bibitem{merriam12} J.~C.~Merriam (1912) The fauna of Rancho La Brea, Part~II:
Canidae. \emph{Mem. Univ. California} 1(2):217--272.
\bibitem{merriamstock25} J.~C.~Merriam \& C.~Stock (1925) \emph{Relationships and
structure of the short-faced bear, Arctotherium, from the Pleistocene of
California}. Carnegie Institution of Washington, Publ.~347.
\bibitem{stock25} C.~Stock (1925) \emph{Cenozoic gravigrade edentates of western
North America}. Carnegie Institution of Washington, Publ.~331.
\bibitem{osborn42} H.~F.~Osborn (1942) \emph{Proboscidea}, vol.~2. American
Museum of Natural History.
\bibitem{payen76} L.~A.~Payen \& R.~E.~Taylor (1976) Man and Pleistocene fauna at
Potter Creek Cave. \emph{J. California Anthropology} 3(1):51--58.
\bibitem{feranec07} R.~S.~Feranec, E.~A.~Hadly, J.~L.~Blois, A.~D.~Barnosky \&
A.~Paytan (2007) Radiocarbon dates from the Pleistocene fossil deposits of Samwel
Cave. \emph{Radiocarbon} 49(1):117--121.
\end{thebibliography}
\end{document}
"""

doc = (PREAMBLE + "\n" + latex_clean(strip_fences(vision)) + "\n\n" + body
       + "\n\n" + latex_clean(strip_fences(conclusion)) + "\n" + BIB)
open("honest-3d.tex", "w").write(doc)
print(f"wrote honest-3d.tex  ({len(doc)} chars, sections: "
      f"{['vision'] + [k for k in ORDER if k in secs] + ['conclusion']})")
print("coherence_fixes to apply:")
for c in w.get("coherence_fixes", []):
    print(f"  - [{c.get('section')}] {c.get('issue')[:80]}")
