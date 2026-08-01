# pronk — Heda, *Still Life with a Gilt Cup*, 1635 — builder research

Source: Willem Claesz Heda, *Stilleven met vergulde bokaal*, 1635. Oil on panel
(4 horizontally grained oak planks), **87.8 × 112.6 cm**. Rijksmuseum **SK-A-4830**,
acquired 1984 (Noortman & Brod, with Vereniging Rembrandt support). Signed
**"HEDA. 1635" on the hem of the napkin, bottom centre-right** — note for us: the
painter's own provenance mark is IN the cloth, at (x≈0.615, y≈0.955). Put ours there.

Reference image (CC0, 5620×4354): `research/ref_pronk_heda_SK-A-4830.jpg`.
Everything below is measured from this image or taken from the Rijksmuseum
catalogue entry and the Rijksmuseum Bulletin acquisition article (W. K[loek],
Bulletin 1984, no. 28, pp. 225–227). Coordinates are (x, y) fractions of the
frame from top-left. The painting is essentially life-size: 1 unit of frame
width ≈ 112.6 cm, so canvas-measured object sizes below are ~real sizes.

---

## 0. The one-sentence diagnosis

Heda's picture is a **single connected silhouette** — every object overlaps its
neighbour in one frieze from x=0.03 to x=0.97, the skyline **staircases up
left→front to right→back**, peaks at the gilt cup, and the whole ridge sits
against a bare graded wall. "Gedisciplineerde wanorde" — *disciplined disorder*
(Bulletin). If our version reads as an arrangement, it is because our objects
don't touch, don't overlap, and don't share one skyline.

---

## 1. THE PICTURE — construction

### 1.1 Geometry / camera
- **Frame aspect 112.6:87.8 = 1.283:1** (landscape). Render at this ratio.
- **Table back edge (table–wall junction): y ≈ 0.575**, horizontal, parallel to
  the picture plane. This is the "low horizon" of the brief: the tabletop
  surface occupies only a narrow wedge; the wall is ~55% of the frame area.
- **Camera square-on** to the table front edge. Verticals are vertical.
- **Elevation:** the 35 cm charger's ellipse is ≈ 1:3.6 (minor:major) →
  viewpoint ≈ **16° above the tabletop plane**. At ~1.9 m to the charger
  centre that is eye ≈ **50 cm above the tabletop**. Mild perspective —
  near-life-size feel, so a longish lens: **~35–40° horizontal FOV**.
- All ellipses (plate rims, drinking rims, foot rings) must be consistent with
  that ONE camera height. The Bulletin singles out exactly this — "the
  difficulty of the perspective, with all those awkward circles-become-ellipses
  of dishes, of drinking rims of glass and silver" — as the painting's
  demonstration piece. Inconsistent ellipses are the fastest way to break it.

### 1.2 The two diagonals
- **Main diagonal (the "strenge diagonaal", Bulletin):** the object skyline
  rises from the overhanging plate at lower-left (0.06, 0.78) through charger →
  bread (0.42, 0.68) → roemer rim (0.55, 0.30) → **gilt-cup finial (0.685,
  0.02)**, then steps down once to the jug lid (0.87, 0.14). One rising line,
  peak just right of centre, one echo-step after the peak.
- **Counter-movements:** the tipped tazza's axis points down-left (foot at
  0.56, 0.62 → bowl at 0.72, 0.45); the knife points down-right at the viewer
  (0.55, 0.66 → ball tip 0.65, 0.70); the lemon peel makes a dead **vertical
  drop** at x ≈ 0.885 (0.55 → 0.79); the napkin cascade falls vertically over
  the front edge at centre-right. Rising ridge, falling accents.

### 1.3 Nearest the viewer / frame breaks
- **Front-left: the small pewter plate of empty oyster shells + pepper cone
  PROJECTS over the table edge**, hovering into the viewer's space — the
  repoussoir. Its underside is in shadow against the bright cloth. Bulletin:
  the plates set "carelessly" over the edge are deliberate, "to create an
  interesting rhythm of shadows."
- **Right edge: the overturned berkemeyer is CROPPED by the frame** — only
  ~60% of it visible, lying on its side. The picture deliberately continues
  past the frame.
- **Top: the gilt cup's pike finial stops ~2% short of the top edge.** Tension,
  no touch.
- **Left: cloth corner keeps a ~6% margin.** Bottom: dark under-table strip
  ~4% tall runs the full width.
- The **knife bridges the dark green wedge** between the two white napkins and
  points its handle at the viewer — the invitation into the picture.

### 1.4 Light
- **Source: a cross-mullioned casement window (kruiskozijn) high to the
  viewer's LEFT, out of frame.** Not inferred — *painted*: the window's cross
  is mirrored in the roemer's bowl upper-left, and refracted AGAIN as a warm
  patch through the wine on the bowl's lower right. Reproduce both or the
  glass will look fake.
- Direction ≈ **azimuth 40° left of camera axis, elevation ≈ 35°**. Soft
  window-sized source (~1 × 1.2 m at ~2 m): shadows have clear direction but
  soft edges. All cast shadows fall to the RIGHT and slightly toward the
  viewer.
- Colour: **cool-neutral daylight (~5200 K)** against a warm umber wall; weak
  warm fill from the right wall bounce, key:fill ≈ 4:1.
- **Wall gradient (bake it, X_ITE won't do it):** brightest zone (~L55–58)
  behind/around the roemer and gilt cup (x 0.5–0.75, y 0.1–0.4), falling to
  ~L35 at the left edge, top corners, and behind the jug's right side. The
  gradient is a quiet halo that puts the brightest wall behind the most
  saturated object. No texture on the wall — Heda's ground is a thin smooth
  whitish layer; keep it as a clean gradient, zero noise.
- **What stays dark:** the under-table strip, the exposed green-carpet wedge
  centre-front, the jug's shadow side, the shadow valley between napkin folds.
  These darks are the value anchor; do not fill them.

### 1.5 Tonal key and palette
"Monochrome banketje": mid-key grisaille of greys with **exactly two chroma
accents — the fire-gilt cup and the lemon** (bread crust is the half-accent).
Approximate targets (sRGB):
- Wall: #8A7A6C (bright zone) → #675A4F (corners)
- Napkins: crest highlights #EDE7D8, mid #CFC8B6, fold shadows #9E968A
- Green table carpet: #1F2A1C shadow → #3A4D33 lit crest (bottle green, wool)
- Pewter: body #4C4C44, sheen band #8A8A7C, rim-wear lines #C9C9BB
- Silver (tazza bowl, dulled): #93908A → #B9B6AC; (foot interior, polished):
  #D8D4C8 with near-white speculars
- Gilt cup: shadow #7A4E1C, mid #C08A34, burnished highlight #F0CE7C —
  warm ORANGE gold (fire-gilt), never lemon-yellow
- Roemer glass #5A6B4A; wine in it #C6CC7E, luminous where lit from behind
- Lemon peel #D8B93C, pith #E8E4D4, cut flesh #DFD9A4 wet
- Oyster nacre #D5D4C6, mantle #8A8A70 wet-glossed

### 1.6 Eye path (verify on our render)
Enter at the bright cloth front-left → up the plate/bread diagonal → roemer →
gilt cup (peak) → down the jug → lemon-peel vertical drop → napkin cascade →
knife → back to the plates. A closed circuit; nothing leads out of frame except
the deliberately cropped berkemeyer, which bounces the eye back in.

---

## 2. THE PROPS — every object, with construction and optics

Layout order left→right. Sizes: canvas-measured (≈ life size); trust the
proportions absolutely, the absolute cm to ±10%.

### 2.1 Beaker of red wine (far left, back) — (0.245, 0.47)
Plain thin-walled cylindrical glass tumbler, slightly tapered, ~9 cm h × 7 cm Ø,
half-full of **red wine reading amber-brown** in the grey light (the museum's
"glass with red wine" — in a monochrome banketje even red wine is umber).
Optics: one vertical window highlight, dark liquid mass, rim a hairline of
light. Almost swallowed by the wall — keep it quiet.

### 2.2 Large pewter charger of oysters — centre-left, (0.17–0.485 wide, centre ≈ 0.33, 0.62)
**Ø ≈ 35 cm** pewter charger ("sadware": cast, then hammered/spun, planished),
wide flat rim, shallow well. Holds ~7 opened oysters; more shells scattered on
the cloth; the small front plate holds emptied shells. Pewter optics: **dull
anisotropic sheen** — Bulletin: "few artists could paint the dull sheen of
pewter so beautifully." Roughness ~0.35–0.45, metallic, with faint concentric
turning marks; the BACK RIM picks up smeared vertical reflections of the salt
cellar and cruet standing behind it; the front rim is a bright wear-line.
Never chrome-sharp: reflections are pulled and blurred along the surface.

**Oysters** (Ostrea edulis, the European flat): rounded fan shells ~7–8 cm,
exterior flaky grey-brown, interior **nacre** — pale warm white with grey-green
wet mantle and a glistening body. Optics: interior = high-gloss wet (sharp
small speculars, roughness ~0.08) over soft nacre; exterior matte, laminated,
crumbly-edged. They read as the only *organic wet* passage on the left.

### 2.3 Small pewter plate + pepper cone — front-left, OVERHANGING, (0.06–0.27, centre 0.16, 0.72)
Pewter trencher **Ø ≈ 20 cm**, projecting past the table edge. On it: emptied
oyster shells and a **cone rolled from a PRINTED page — red and black
letterpress clearly legible (an almanac/broadsheet leaf) — holding ground
pepper**. Paper is bright, crisp, the sharpest white-on-dark contrast in the
left half; the print is upside-down and partial. Vanitas: yesterday's news
wraps today's spice. (Provenance opportunity: our in-scene text can live here
as the printed page, exactly as Heda used printed ephemera.)

### 2.4 Bread roll on pewter plate — centre-front, (0.42, 0.68)
Small plate Ø ≈ 20 cm; a white wheat roll **broken open**, crust golden-brown
(#C9973F) with a dull satin gloss — Bulletin notes "the gleam of the crust of
a broodje" as a specialist's touch — crumb pale, matte, open-textured. Not
sliced: torn. Half-eaten = vanitas.

### 2.5 Glass cruet (oil/vinegar jug) — back, (0.38, 0.475)
Façon-de-Venise **colourless soda glass** (faint grey-green), ~12 cm h.
Body a flattened sphere with **wrythen (spiral-twisted) ribs like a scallop
shell**; narrow neck with an applied milled collar ring; thin curved **spout
rising from low on the body to above rim height**; ear-shaped applied handle;
flared mouth. The same vessel reappears in Heda's 1656 Houston still life —
it was a real studio prop. Optics: nearly invisible — it transmits the wall
with slight darkening; renders as **edge highlights + rib glints only**.
Roughness ~0.02, IOR 1.5, thin-walled. If it reads as a solid object, it's
wrong.

### 2.6 Silver salt cellar, heaped — back, (0.475, 0.47), touching the roemer
Cylindrical pedestal salt, **~10 cm drum + salt, Ø ≈ 6.5 cm**, silver. The
entire drum is covered in **fine flat-chased moresque/arabesque scrollwork on
a matted ground** (Bulletin: the reflections "in the engraved surface of the
zoutvat"); moulded foot; projecting serrated/scalloped top flange; the top
depression heaped with **coarse white salt** — the salt sparkles (crisp
micro-speculars, the brightest small whites in the picture). Optics: chased
silver = broken directional sheen — burnished ridges flash, matted ground
stays grey. Model as silver metal, roughness ~0.3, with a chased normal/bump
pattern; the salt as near-white with glints.

### 2.7 Roemer of white wine — THE optical centrepiece, (0.475–0.625 wide, rim 0.295, stem base ~0.60)
**Green Waldglas (forest glass)** roemer, canvas-measured bowl Ø ≈ 17 cm
(display size; historical roemers 17–26 cm tall — build to canvas proportion:
total h ≈ 26 cm). Construction, bottom to top:
- **Foot**: a thread of molten glass spun/coiled around a conical former
  (here hidden behind the napkin and tazza — you may legitimately hide it).
- **Stem**: hollow cylinder fused to the bowl, studded with **3 rows × ~4–5
  raspberry prunts** — applied blobs stamped with a waffle die; they read as
  dark drops with one bright point each.
- A **milled/beaded collar thread** where stem meets bowl.
- **Bowl**: near-spherical cap, slightly incurved rim, wall a few mm thick.
- Colour: grey-olive-green (#5A6B4A), with seeds/small bubbles.
- **Wine: white wine to ~55% of bowl** — reads yellow-green, luminous.
Optics — this must all be present:
1. the **cross-window reflection upper-left of the bowl** (paint/bake it as an
   emissive-ish decal or a lit window card in the reflection environment);
2. the **second, refracted warm window patch in the wine, lower right**;
3. a hairline rim light; 4. the meniscus line; 5. prunt speculars.
IOR 1.5, roughness 0.02–0.05, absorption green. The Bulletin calls out the
window-in-the-roemer as the painting's signature reflection.

### 2.8 Overturned silver tazza — centre-right, (0.53–0.80, y 0.40–0.67)
A **drinking tazza**: wide shallow bowl on a baluster stem and trumpet foot,
Dutch silver, early 17th c. Canvas: bowl **Ø ≈ 19–20 cm**; assembled height
if upright ≈ 14 cm. It lies **on its side, foot toward lower-left, bowl-back
toward upper-right**, so we see (a) the chased UNDERSIDE of the bowl as the
big ellipse: strapwork and pounced arabesques, **star/rosette bosses**, radial
gadroon lobes; (b) the cast **baluster stem with a berry-cluster knop and two
scrolled brackets, each with a small pendant ring dangling** (they hang by
gravity — a cue the object is truly tipped); (c) the **inside of the trumpet
foot facing the viewer**: the reverse (intaglio) of the foot's embossing reads
as a froth of bright bubbles.
**The Bulletin's key observation — build this contrast:** "the somewhat DULLED
silver of the drinking bowl against the still fully POLISHED inner side of the
foot" — the handled bowl is oxidised toward matte grey (roughness ~0.35),
the protected foot interior is bright mirror (roughness ~0.08) and carries the
sharpest silver highlights in the picture. Also per the Bulletin: **the creased
white napkin is visibly REFLECTED in the tazza bowl** — the silver picks up a
soft white smear from the cloth below it. Same tazza appears tipped in Heda's
1634 Boymans picture — his favourite virtuoso prop.

### 2.9 Gilt cup and cover (the "vergulde bokaal") — the peak, (0.60–0.77, y 0.02–0.47)
Silver-gilt (**fire-gilt**) covered standing cup, Nuremberg/Dutch type,
c. 1600–1630. Canvas height with cover ≈ **40–45 cm** — tallest object.
Bottom to top:
- spreading domed foot, embossed scrollwork on pounced ground (partly hidden
  behind the tazza);
- large **embossed knop with lobes and acanthus scrolls**; moulded rings;
- a spool-shaped stem section with a **band of circular medallion bosses**;
- wide low **cup with rounded underbody**, its whole surface pounced/matted
  and chased with strapwork;
- low-domed **cover with an embossed scrollwork frieze** and a smooth flange;
- baluster finial carrying a **cartouche shield and a soldier/Mars figure
  holding a pike** — the pike is the picture's highest point.
- Small **pendant rings hang from the stem brackets** (visible lower left of
  the stem), like the tazza's.
Optics: fire-gilding is warm orange gold. Burnished ridges + flange rims flash
(roughness ~0.15); the pounced/matted grounds sparkle as **granular
micro-speckle** (roughness ~0.4 with a fine bump). Left flank takes the cool
window key; right flank takes warm wall bounce; and it must **reflect
recognisably in the pewter jug beside it** (Bulletin: "the reflection of the
gilt bokaal in the pewter jug"). This is the No.1 chroma accent — everything
else grey supports it.

### 2.10 Pewter flagon (wine jug), LID OPEN — right, (0.72–0.97, y 0.14–0.53)
Dutch pewter flagon ("Jan Steen jug" family): **pear-shaped body** with fillet
mouldings at waist and base, **trumpet-flared neck**, flat strap handle with
long tail, hinged **flat-domed lid standing OPEN ~110°**, twin-ball
thumbpiece. Canvas height (incl. open lid) ≈ 33 cm; body Ø ≈ 17 cm. Surface:
darker, more olive than the plates; scratches, small dents, a bright wear-line
on the rim; the open lid's interior is dark.
Reflection inventory (all present in the painting): **warm gold smear of the
bokaal on its left shoulder/neck**, a cool vertical window streak on the neck,
a soft white glow from the napkin at its base. The open lid = vanitas: the
jug stands emptied. Roughness ~0.3–0.4 metallic, blur its reflections.

### 2.11 Half-peeled lemon — right accent, ON the green carpet, (0.885, 0.55–0.79)
Lemon Ø ≈ 7 cm, top third peeled; **cut face toward the viewer** showing
radial segments, wet-glossy (#DFD9A4, roughness ~0.1); the **peel unwinds in
one connected ~30 cm ribbon**, ~2 cm wide, pith-side (white, flocculent, matte)
alternating with the bumpy oil-pocked zest (#D8B93C, satin) as the ribbon
twists — it drops **vertically** down the carpet and curls at rest. Bulletin:
"the wet surface of a freshly peeled lemon" is one of the named virtuoso
passages. Vanitas: fair without, sour within.

### 2.12 Overturned berkemeyer — far right, CROPPED, (0.90–1.00, y 0.50–0.65)
A berkemeyer (the roemer's straight-sided cousin): **conical funnel bowl** on
a prunted hollow cylinder, dark green Waldglas, lying on its side, mouth
toward lower-right, **cut by the frame edge**. Nearly black in the shadow;
one long bright window streak runs inside the cone. Second overturned vessel
= the revel is over. Keep it dark; it is a punctuation mark, not a feature.

### 2.13 Behind the lemon: a dim pewter plate on edge, (0.93, 0.55)
Barely-lit ellipse of another plate lying at the back right on the carpet.
Optional but it thickens the right-side shadow zone.

### 2.14 Knife — centre-front, (0.53–0.66, y 0.63–0.71)
Table knife ~19 cm: short steel blade **slipped under the napkin fold**
(mostly hidden — only the ricasso shows), chased silver bolster/ferrule,
handle of dark tortoiseshell/ebony set with **three rows of silver piqué
studs**, terminating in a small ball button. Bulletin: "the collection of
light-points on the knife haft" — **every stud gets its own specular point**.
It lies on the dark green wedge between the napkins, pointing out of the
picture toward the viewer's right hand.

### 2.15 The cloths — the stage itself
Three textiles, and they do different jobs:
- **Green wool table carpet (the actual tablecloth)**: deep bottle green,
  napped/matte (roughness ~0.7), covers the whole table; exposed as (a) the
  dark WEDGE centre-front between the napkins, (b) the right-hand tabletop
  under lemon/jug, (c) a sliver at the right end of the table edge.
- **Napkin 1 — spread, left half**: white linen **damask** laid flat over the
  carpet, falling over the front-left corner in long straight folds. It still
  carries its **pressed crease grid** — sharp fold lines from storage,
  dividing it into rectangles; the front drop has one knife-edge vertical
  crease. Signature Heda/Claesz motif; model the creases, not generic cloth
  ripples.
- **Napkin 2 — crumpled, centre-right**: bunched under the tazza and
  **cascading over the front edge** in a bright triangular waterfall; hems
  visible with drawn-thread borders and dotted stitching; **"HEDA. 1635"
  sits on this hem**.
- Damask optics: satin-float weave = **directional sheen**; highlight sweeps
  across the fold crests (anisotropic, roughness ~0.35 along / 0.6 across);
  the woven figure appears ONLY where the sheen grazes — white-on-white,
  visible in the crumpled napkin's lit crests. Shadow side of folds goes
  warm-grey, never blue.

### 2.16 Table
Sturdy rectangular table, top ~78 cm off the floor (standard), front edge
parallel to the picture plane, length > frame (both ends exit the frame edges
left; right end is just inside, covered by carpet at (0.97, 0.55)). Under-table
darkness is a flat near-black band — no floor detail whatsoever.

---

## 3. Vanitas program (what the objects SAY, so we keep the reading)

overturned tazza + overturned berkemeyer (the feast is over) · open, emptied
oyster shells (luxury, appetite, transience) · torn half-eaten bread ·
half-peeled lemon (beauty peeled to sourness) · pepper in yesterday's printed
page (ephemera of the world) · open-lidded emptied flagon · knife (severance)
· the still-full roemer and untouched gilt cup standing upright above it all:
what remains when appetite is done. No skull, no watch — Heda's vanitas is
entirely in the state of the meal.

---

## 4. Direct build checklist (delta from "arrangement" to "picture")

1. **One frieze**: force overlaps — plate over table edge, cruet behind
   charger rim, salt touching roemer, tazza foot into napkin, bokaal behind
   tazza bowl, jug behind bokaal, lemon in front of jug. No isolated object.
2. **One skyline**: staircase up to the bokaal at x≈0.68, one step down (jug),
   then fall to the cropped berkemeyer.
3. **Camera**: eye ~50 cm above tabletop, ~1.9 m back, square-on, 35–40° FOV,
   frame 1.283:1, table-wall line at y≈0.575.
4. **Bake the wall gradient** (bright halo behind roemer/bokaal, dark corners)
   and **bake contact shadows** to the right of every foot — X_ITE renders no
   shadows (known).
5. **Two chroma accents only** (gold, lemon); everything else within the
   grey-green-umber envelope of §1.5.
6. **The named reflections** (§2.7, 2.8, 2.9, 2.10, 2.14): window-cross in
   roemer, wine-refracted window, bokaal-in-jug, napkin-in-tazza, polished
   foot interior vs dulled bowl, per-stud knife sparks. These are what made
   Heda famous; four of the six are cheap decals/material splits for us.
7. **Crop the berkemeyer** at the right frame edge; overhang the shell plate
   at front-left; near-touch the top with the pike.
8. **Provenance in-scene**: the printed pepper-paper (2.3) and/or the signed
   napkin hem (2.15) are the historically honest carriers.
9. Vanitas states, not pristine props: tazza and berkemeyer DOWN, flagon lid
   OPEN, bread TORN, lemon HALF-peeled, shells EMPTY.

## 5. Sources

- Rijksmuseum collection entry SK-A-4830 (dimensions, support,
  dendrochronology 1605/ready ~1616–22, full object list, provenance,
  condition): https://www.rijksmuseum.nl/en/collection/SK-A-4830
- Rijksmuseum Bulletin 32 (1984) no. 28, pp. 225–227, W. K. — acquisition
  article; source of: "strenge diagonaal", disciplined disorder, plates over
  the edge for shadow rhythm, the named reflections (kruiskozijn in roemer,
  creased cloth in tazza, bokaal in pewter jug, light-points on knife haft,
  engraved zoutvat), dulled-bowl vs polished-foot contrast, tazza reuse in
  Dresden 1631 / Rijksmuseum + Boymans 1634, cruet reuse in Houston 1656.
  PDF: https://bulletin.rijksmuseum.nl/article/download/20695/22346/50629
- Rijksmuseum "100 masterpieces" story (tonal banketje, master-of-reflections,
  pewter sheen): https://www.rijksmuseum.nl/en/stories/one-hundred-masterpieces/story/still-life-gilt-cup
- Wikimedia Commons CC0 file (the 5620×4354 reference):
  https://commons.wikimedia.org/wiki/File:Stilleven_met_vergulde_bokaal_Rijksmuseum_SK-A-4830.jpeg
- Roemer construction (Waldglas, prunt stamping, spun/coiled foot, period
  dimensions): Scottish Antiques roemer pages + Allaire Collection glass blog
  (https://ancientglass.wordpress.com/variations-in-glass-art-and-style/roemer-type-wine-and-beer-glasses-from-the-16th-century-to-present/)
- All coordinates, colour targets, ellipse/elevation math: measured from the
  CC0 reference image in this directory.
