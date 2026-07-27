# Interconnecting X3D Worlds: Inlining, Anchors, and Cross-World Wiring

A practical guide to the mechanisms that turn a set of separate `.x3d`
files into a single navigable, interconnected system. Written to
accompany the example files `hub.x3d`, `satelliteA.x3d`,
`satelliteB.x3d`, and `deepworld.x3d` — every concept below is wired up
in those files, and section headers point to the relevant lines.

---

## The core distinction

X3D gives you two fundamentally different ways to bring another world
into the picture, and they answer two different questions:

| Mechanism | Question it answers | When the other world appears |
| --------- | ------------------- | ---------------------------- |
| **`Inline`** | "What is part of *this* scene?" | Immediately (or on demand), embedded in the current hierarchy |
| **`Anchor`** | "Where can the user *go*?" | On user activation — a hyperlink jump |

Everything else is built on top of these two. `Inline` is composition;
`Anchor` is navigation. A web of worlds usually needs both: `Inline`
to assemble a persistent space out of streamable parts, and `Anchor`
to let the user leap between spaces that shouldn't all be resident at
once.

---

## 1. `Inline` — embedding a world as a node

An `Inline` node loads an external X3D file and grafts its scene graph
into the current one at the point where the node sits. The embedded
content inherits the parent's transformation hierarchy: wrap an
`Inline` in a `Transform translation="-10 0 0"` and the whole child
world is shifted ten units west.

```xml
<Inline DEF="SatA" load="false"
        url='"satelliteA.x3d"'
        bboxCenter="0 1 0" bboxSize="4 4 4"/>
```

Field by field:

- **`url`** is a *list* of candidates in fallback order. The browser
  tries each until one loads:
  `url='"satelliteA.x3d" "satelliteA.wrl" "https://backup.example/satA.x3d"'`.
  Note the quoting: it's a single MFString attribute containing
  space-separated, double-quoted tokens.
- **`load`** (X3D 3.2+) controls *deferred* loading. With
  `load="false"` the file is named but not fetched. Flip it to `TRUE`
  later — via a `ROUTE` — and the world streams in on demand. This is
  the foundation of proximity paging (§4).
- **`bboxCenter` / `bboxSize`** declare the child's bounding box
  *without* the browser having to parse the file. This lets the
  renderer cull an off-screen Inline, or decide not to bother loading
  a deferred one that's nowhere near the viewer. Supplying an accurate
  bbox is a real performance lever for large scenes; an absent or wrong
  one defeats culling.

### The namespace boundary — the important caveat

An Inlined file's `DEF` names live in their **own isolated
namespace**. This has two consequences that trip people up:

1. **Good:** `DEF` names never collide. You can Inline twenty copies
   of a world that all internally `DEF` a node `Spinner`, and nothing
   clashes.
2. **Constraining:** you **cannot** `ROUTE` an event into an Inlined
   node by name, because that name isn't visible in the parent scope.
   A `ROUTE fromNode="HubClock" toNode="Spinner"` simply can't see a
   `Spinner` that lives inside an Inline.

That second point is exactly what `IMPORT`/`EXPORT` exists to solve
(§3). Without it, an Inline is a sealed box: it renders, but the parent
can't reach inside to animate or control it.

---

## 2. `Anchor` — hyperlinking between worlds

`Anchor` is a grouping node that behaves like an HTML `<a>` tag. Its
children are clickable geometry; activating them loads a new world or
jumps within the current one.

```xml
<Anchor description="Portal to Deep World"
        url='"deepworld.x3d#Arrival"'>
  <Shape>
    <Appearance><Material diffuseColor="0.9 0.4 0.1"/></Appearance>
    <Sphere radius="0.8"/>
  </Shape>
</Anchor>
```

- **`description`** is the tooltip / status-bar text the browser shows
  on hover. Always set it — it's the user's only cue that geometry is
  clickable.
- **`url`** is again an MFString fallback list.
- **`parameter`** passes hints like `'"target=_blank"'` to control
  *where* the world opens (relevant when the X3D scene is embedded in
  an HTML page).

### The `#ViewpointName` fragment — the key to smooth transitions

The `#Arrival` suffix is a **viewpoint fragment**. It tells the
browser: load this world, then immediately bind the `Viewpoint` whose
`DEF` is `Arrival`. The result is that the user lands at a known
position, correctly oriented, instead of at the file's default
viewpoint.

```xml
<!-- In deepworld.x3d: -->
<Viewpoint DEF="Arrival" description="Arrival"
           position="0 1.6 8" orientation="0 1 0 0"/>
```

The same fragment syntax works for jumps *within* the current world —
`url='"#SomeViewpoint"'` with no filename re-binds a viewpoint without
reloading anything. This is how you build "look over here" hotspots.

Pairing a portal `Anchor` with a matching named arrival `Viewpoint` is
the single most important trick for making world-to-world travel feel
continuous rather than disorienting. Build them as a matched set: every
portal that goes *somewhere* should target a viewpoint that's been
placed to receive arrivals (e.g. facing back toward the return portal).

### Round-tripping

`deepworld.x3d` contains a return `Anchor` pointing at
`hub.x3d#Entry`. Two worlds, each with an `Anchor` into the other and
each with a named landing `Viewpoint`, form a complete bidirectional
portal pair. Scale that up and you have a graph of worlds connected by
labeled doorways.

---

## 3. `IMPORT` / `EXPORT` — live wiring across the boundary

This is the mechanism that elevates a collection of nested static
geometry into an actually *interconnected* system: it lets events flow
across the Inline namespace boundary, so a node in one file can drive a
node in another.

It's a two-sided handshake.

**Child side** — the Inlined file must explicitly publish a node:

```xml
<!-- In satelliteB.x3d -->
<Transform DEF="RemoteSpin"> ... </Transform>
<EXPORT localDEF="RemoteSpin" AS="RemoteSpin"/>
```

`EXPORT` says: "my node `RemoteSpin` is available to whoever Inlines
me, under the exported name `RemoteSpin`." Only EXPORTed nodes are
reachable; everything else stays sealed.

**Parent side** — the file containing the `Inline` imports that
published node into its own namespace:

```xml
<!-- In hub.x3d -->
<Inline DEF="SatB" url='"satelliteB.x3d"'/>
<IMPORT inlineDEF="SatB" exportedDEF="RemoteSpin" AS="SatB_Spin"/>
```

`IMPORT` reads: "from the Inline I `DEF`'d as `SatB`, take its exported
node `RemoteSpin`, and give it the **local** name `SatB_Spin`." From
this point on, `SatB_Spin` is a routable handle in the parent scene.

**Then you ROUTE to it like any local node:**

```xml
<TimeSensor DEF="HubClock" cycleInterval="6" loop="true"/>
<OrientationInterpolator DEF="SpinPath"
    key="0 0.5 1"
    keyValue="0 1 0 0  0 1 0 3.14159  0 1 0 6.28318"/>

<ROUTE fromNode="HubClock" fromField="fraction_changed"
       toNode="SpinPath"  toField="set_fraction"/>
<ROUTE fromNode="SpinPath" fromField="value_changed"
       toNode="SatB_Spin" toField="set_rotation"/>
```

The hub's clock now spins a box that physically lives in a different
file. *That* is the bootstrap mechanism for a web of worlds — not the
nesting, but the event flow across the seam.

### Two operational caveats

- **`IMPORT` only resolves after the Inline has loaded.** If the target
  Inline is currently paged out (`load="false"`, §4), a cross-world
  ROUTE into it simply lies dormant and resumes when the world reloads.
  Usually what you want — but it means remote state does **not**
  persist across an unload/reload cycle. Don't rely on an IMPORTed node
  to remember anything between unloads.
- **`IMPORT`/`EXPORT` carry events, not geometry.** They don't move
  shapes between files; they expose a handle so routes can cross. The
  geometry stays where it's authored.

---

## 4. Proximity paging — loading worlds as you approach

Combine deferred `Inline` (`load="false"`) with a `ProximitySensor` and
you get worlds that stream in when the avatar gets close and unload
when it leaves — bounding memory to roughly "what's nearby."

```xml
<Transform translation="-10 0 0">
  <ProximitySensor DEF="ProxA" size="12 12 12" center="0 0 0"/>
  <Inline DEF="SatA" load="false" url='"satelliteA.x3d"'/>
</Transform>
```

A `ProximitySensor` fires events whenever the viewer is inside its box:

- **`enterTime`** — an `SFTime` emitted at the moment of entry.
- **`exitTime`** — `SFTime` emitted on exit.
- **`isActive`** — an `SFBool`, `TRUE` while inside, `FALSE` on leaving.
- **`position_changed` / `orientation_changed`** — the viewer's pose
  *relative to the sensor*, handy for proximity-driven effects.

The cleanest wiring uses `isActive` directly, since it's already the
boolean `load` wants:

```xml
<ROUTE fromNode="ProxA" fromField="isActive" toNode="SatA" toField="load"/>
```

Enter the box → `isActive=TRUE` → `SatA.load=TRUE` → world streams in.
Leave → `isActive=FALSE` → world unloads. The example also shows a
`TimeTrigger`-based variant (converting `enterTime` into a `TRUE`
pulse) for cases where you want enter and exit handled by separate
nodes.

### Browser-compatibility note

Browsers vary in how strictly they coerce `SFTime` → `SFBool` through
helper nodes like `TimeTrigger`/`BooleanFilter`. The bulletproof
fallback, if a satellite refuses to load declaratively, is a tiny
`Script` node that listens to `isActive` and sets `load`:

```xml
<Script DEF="PagerA" directOutput="true">
  <field accessType="inputOnly"   name="active" type="SFBool"/>
  <field accessType="initializeOnly" name="target" type="SFNode">
    <Inline USE="SatA"/>
  </field>
  <![CDATA[
    ecmascript:
    function active(v) { target.load = v; }
  ]]>
</Script>
<ROUTE fromNode="ProxA" fromField="isActive" toNode="PagerA" toField="active"/>
```

Routing `isActive` straight into `load` (no helper nodes) is the most
widely supported declarative approach and is what to reach for first.

### `VisibilitySensor` — the alternative trigger

Where `ProximitySensor` keys off *distance*, `VisibilitySensor` keys
off whether a region is *in the view frustum*. Swap it in when you want
to load a world because the user is **looking toward** it rather than
because they're **near** it — useful for distant landmarks that should
resolve as they come into view.

---

## Putting it together: the hub-and-spoke pattern

The example files implement a standard, scalable topology for
interconnected worlds:

```
                    deepworld.x3d
                   (Anchor portal,
                    own namespace,
                    return Anchor)
                         ▲
                         │  click / #Arrival
                         │
   satelliteA.x3d ◄──────┴──────► satelliteB.x3d
   (proximity-paged,          (proximity-paged,
    self-animating,            EXPORTs RemoteSpin,
    isolated)                  driven by hub clock)
        ▲                              ▲
        │ ProximitySensor              │ IMPORT + ROUTE
        │ + Inline load=false          │ + Inline load=false
        └──────────────┬───────────────┘
                       │
                   hub.x3d
              (always resident:
               pillar + ground,
               master clock,
               all the wiring)
```

The design principles this encodes:

1. **A lightweight persistent hub** stays loaded the whole session. It
   holds only what must always be present — here, a marker pillar and
   ground plane — plus the orchestration logic (the master clock and
   every ROUTE).
2. **Satellites are deferred Inlines, paged by proximity.** Memory
   tracks the avatar, not the whole world graph. Add a hundred
   satellites and only the nearby few are ever resident.
3. **Cross-world control flows through IMPORT/EXPORT.** Satellite B's
   spinner is animated by the hub, demonstrating that a paged-in world
   can be wired into the hub's logic rather than being inert.
4. **Heavyweight or rarely-visited destinations are Anchor portals,**
   not Inlines. `deepworld.x3d` is reached by an explicit click and
   loads as a full scene swap with a named arrival viewpoint — the
   right choice when a world is big enough that you never want it
   resident alongside the hub.

The result scales: the hub is a switchboard, satellites are
hot-swappable panels, and portals are doorways to spaces too large to
keep in the same room.

---

## Quick reference

| I want to… | Use |
| ---------- | --- |
| Embed another world as part of this scene | `Inline` |
| Defer that embedding until needed | `Inline load="false"` + ROUTE to `load` |
| Let the browser cull/skip without parsing | `bboxCenter` / `bboxSize` on the Inline |
| Send the user to another world on click | `Anchor url='"world.x3d"'` |
| Land them at a specific spot on arrival | `Anchor url='"world.x3d#ViewpointName"'` + matching `DEF`'d `Viewpoint` |
| Re-aim the camera without reloading | `Anchor url='"#ViewpointName"'` |
| Animate/control a node inside an Inline | `EXPORT` (child) + `IMPORT` (parent) + `ROUTE` |
| Stream a world in when the avatar nears | `ProximitySensor.isActive` → `Inline.load` |
| Stream a world in when it's looked at | `VisibilitySensor` → `Inline.load` |

---

## Files in this set

- **`hub.x3d`** — persistent hub; proximity-paged Inlines; master
  clock; IMPORT of Satellite B's spinner; Anchor portal to the deep
  world.
- **`satelliteA.x3d`** — self-contained, self-animating world paged in
  by proximity; demonstrates namespace isolation (its local clock is
  fully independent of the hub).
- **`satelliteB.x3d`** — EXPORTs `RemoteSpin` so the hub clock can drive
  its rotation across the file boundary.
- **`deepworld.x3d`** — standalone Anchor destination with a named
  `Arrival` viewpoint and a return Anchor back to `hub.x3d#Entry`.

Keep all four in the same directory so the relative `url` references
resolve. Open `hub.x3d` in any X3D 4.0 browser — Castle Model Viewer,
X3DOM in a web page, or FreeWRL.
