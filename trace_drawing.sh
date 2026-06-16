#!/usr/bin/env bash
# Faithfully trace a B&W line drawing (cave plan/section) into vector SVG.
#   PDF:  trace_drawing.sh <in.pdf> <page> "<WxH+X+Y @300dpi>" <out-prefix>
#   PNG:  trace_drawing.sh <in.png> -    "<WxH+X+Y>"          <out-prefix>
# Pipeline: pdftoppm 300dpi -> crop -> threshold (bilevel) -> potrace -> SVG.
set -e
IN="$1"; PAGE="$2"; CROP="$3"; OUT="$4"
if [[ "$IN" == *.pdf ]]; then
  pdftoppm -png -r 300 -f "$PAGE" -l "$PAGE" "$IN" "${OUT}_p"
  PG=$(ls "${OUT}_p"-*.png | head -1)
else PG="$IN"; fi
magick "$PG" -crop "$CROP" +repage "${OUT}_crop.png"
magick "${OUT}_crop.png" -colorspace Gray -threshold 62% "${OUT}.pbm"
potrace "${OUT}.pbm" -b svg --tight -o "${OUT}.svg"
magick -density 150 -background white "${OUT}.svg" "${OUT}_traced.png"
rm -f "${OUT}.pbm" "${OUT}_p"-*.png
echo "wrote ${OUT}.svg (+ _crop.png, _traced.png)"
