# Canonical X3D tooling

External tools used by the generators (`generate_runner.py`,
`generate_classroom.py`) for the Web3D-canonical pipeline.

## Generation — x3d.py
Official Web3D Python package; produces validated X3D node objects.
```
pip install x3d        # 4.0.65.3+ used here
```

## X3D → X3DOM/X_ITE — X3dToX3dom.xslt + Saxon
`X3dToX3dom.xslt` (committed) is the official Web3D stylesheet
(https://www.web3d.org/x3d/stylesheets/X3dToX3dom.xslt). It is XSLT 2.0,
so it needs Saxon (not libxslt/xsltproc). The Saxon jar is gitignored
(5.5 MB binary); fetch it once:
```
curl -L -o tools_x3d/saxon9he.jar \
  https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/9.9.1-8/Saxon-HE-9.9.1-8.jar
```
Convert (the generators do this automatically):
```
java -cp tools_x3d/saxon9he.jar net.sf.saxon.Transform \
  -s:scene.x3d -xsl:tools_x3d/X3dToX3dom.xslt -o:scene.html \
  urlX3DOM=https://x3dom.org/download/1.8.3
```

## Known limitation
Current X3DOM cannot render an HAnim skeleton (and trips a MutationObserver
init bug on large animated scenes). The runner HTML is therefore produced
from a flattened twin (HAnim nodes -> Transform/Group). The authoritative
`.x3d` keeps real HAnim nodes and renders in desktop players
(Castle Model Viewer, X3D-Edit/Xj3D).
