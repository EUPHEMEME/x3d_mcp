# Technē build transcript — studio spine

Audit log of `build_anatomy_spine.py` authoring `build_anatomy/studio_spine.x3d` call-by-call through the Technē stdio proxy.

## Run header

- **Timestamp:** 2026-08-31T01:21:57
- **Technē git SHA:** `de315a9`
- **TECHNE_PROFILE:** `core,coherence,instrumentation`

## Totals

| tool calls | blocked | repaired |
|---:|---:|---:|
| 48 | 0 | 0 |

Clean run: every call passed the rule engine unmodified.

## Calls

| # | tool | args |
|---:|---|---|
| 1 | `create_scene` | description=LOA5 Anatomy Explorer — st, profile=Interactive |
| 2 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 3 | `def_node` | node_id=7e350735-fdd4-4160-93ee-85, name=VP_Body |
| 4 | `add_child` | parent_id=scene, child_id=7e350735-fdd4-4160-93ee-85 |
| 5 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 6 | `def_node` | node_id=3cd9308e-c175-4a14-8453-e3, name=VP_Skull |
| 7 | `add_child` | parent_id=scene, child_id=3cd9308e-c175-4a14-8453-e3 |
| 8 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 9 | `def_node` | node_id=ed5912a7-6b40-42c6-a3e7-83, name=VP_Ribcage |
| 10 | `add_child` | parent_id=scene, child_id=ed5912a7-6b40-42c6-a3e7-83 |
| 11 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 12 | `def_node` | node_id=4ed1fcb3-21e6-4ab1-885a-77, name=VP_Spine |
| 13 | `add_child` | parent_id=scene, child_id=4ed1fcb3-21e6-4ab1-885a-77 |
| 14 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 15 | `def_node` | node_id=c9c4a8cd-33bc-4f98-bb25-6c, name=VP_Hand |
| 16 | `add_child` | parent_id=scene, child_id=c9c4a8cd-33bc-4f98-bb25-6c |
| 17 | `create_node` | node_type=Viewpoint, fields[description,position,centerOfRotation,orientation,fieldOfView,nearDistance,farDistance] |
| 18 | `def_node` | node_id=bc1939ec-4f74-4cfa-8035-f6, name=VP_Foot |
| 19 | `add_child` | parent_id=scene, child_id=bc1939ec-4f74-4cfa-8035-f6 |
| 20 | `create_node` | node_type=NavigationInfo, fields[type,headlight,speed] |
| 21 | `def_node` | node_id=8f10a52c-e6d0-4e9b-b284-8a, name=Nav |
| 22 | `add_child` | parent_id=scene, child_id=8f10a52c-e6d0-4e9b-b284-8a |
| 23 | `create_node` | node_type=DirectionalLight, fields[direction,color,intensity,ambientIntensity,shadows,shadowIntensity,global_,on] |
| 24 | `def_node` | node_id=4cf4e66f-6088-448a-96c8-b8, name=KeyLight |
| 25 | `add_child` | parent_id=scene, child_id=4cf4e66f-6088-448a-96c8-b8 |
| 26 | `create_node` | node_type=DirectionalLight, fields[direction,color,intensity,ambientIntensity,global_,on] |
| 27 | `def_node` | node_id=226af4a8-7f8a-4b11-bf8c-61, name=FillLight |
| 28 | `add_child` | parent_id=scene, child_id=226af4a8-7f8a-4b11-bf8c-61 |
| 29 | `create_node` | node_type=DirectionalLight, fields[direction,color,intensity,ambientIntensity,global_,on] |
| 30 | `def_node` | node_id=3585728b-788f-4ab2-a903-cb, name=RimLight |
| 31 | `add_child` | parent_id=scene, child_id=3585728b-788f-4ab2-a903-cb |
| 32 | `create_node` | node_type=EnvironmentLight, fields[color,intensity,ambientIntensity,global_,on] |
| 33 | `def_node` | node_id=8de3d998-d5db-43c9-a3ee-61, name=Ambient |
| 34 | `add_child` | parent_id=scene, child_id=8de3d998-d5db-43c9-a3ee-61 |
| 35 | `create_node` | node_type=Background, fields[skyAngle,skyColor,groundAngle,groundColor] |
| 36 | `def_node` | node_id=dcfa3540-4fa5-4774-89e8-1b, name=Sky |
| 37 | `add_child` | parent_id=scene, child_id=dcfa3540-4fa5-4774-89e8-1b |
| 38 | `create_node` | node_type=TimeSensor, fields[cycleInterval,loop,enabled] |
| 39 | `def_node` | node_id=a94a7be1-d1de-4a8f-9656-ed, name=WalkTimer |
| 40 | `add_child` | parent_id=scene, child_id=a94a7be1-d1de-4a8f-9656-ed |
| 41 | `create_node` | node_type=TimeSensor, fields[cycleInterval,loop,enabled] |
| 42 | `def_node` | node_id=4eeaf292-0983-4719-9298-81, name=RunTimer |
| 43 | `add_child` | parent_id=scene, child_id=4eeaf292-0983-4719-9298-81 |
| 44 | `create_node` | node_type=TimeSensor, fields[cycleInterval,loop,enabled] |
| 45 | `def_node` | node_id=9a36fe06-23f6-4c53-81ec-f9, name=JumpTimer |
| 46 | `add_child` | parent_id=scene, child_id=9a36fe06-23f6-4c53-81ec-f9 |
| 47 | `validate_current_scene` | — |
| 48 | `get_scene` | encoding=xml |
