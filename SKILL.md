# SKILL.md — Nano Banana–like Local Image Reasoning Skill

## Mission
Turn the current AI-Assistant local image stack into a planner-driven system that behaves closer to Nano Banana 2:
- understands natural-language image requests
- plans before generation
- preserves character continuity
- preserves prop/scene continuity
- supports single-panel and comic multi-panel workflows
- uses ComfyUI as execution, not as the reasoning brain
- uses detector/inpaint/correction loops after generation

## Core rule
Do **not** jump straight from user prompt to image generation.

Always follow this chain:

1. Parse user intent
2. Build character state
3. Build prop/scene state
4. Decide single-panel vs multi-panel
5. Produce structured panel specs
6. Produce execution plan
7. Run ComfyUI stages
8. Evaluate result
9. Patch only the failed regions or failed panel
10. Export final result

## Non-negotiable constraints
- Preserve the existing working local image generation flow where possible.
- Reuse the current project structure instead of rewriting the whole app.
- Keep ComfyUI modular and stage-based.
- Character continuity must be explicit state, not just repeated prose.
- Prop continuity must be explicit state, not just repeated prose.
- Text overlays, title bars, phone UI, and comic bubbles should preferably be rendered as overlays, not trusted to the image model.
- Do not treat prompt enhancement as true reasoning.
- Do not invent a second separate production runtime if the current pipeline can be extended.
- Favor additive integration.

## What counts as Nano Banana–like behavior
A system is closer to Nano Banana 2 if it:
- understands intent before generation
- breaks a story into meaningful panels
- keeps the same character stable across panels
- keeps recurring props stable across panels
- reuses memory from earlier panels
- knows when to inpaint instead of regenerating the whole panel
- evaluates continuity and retries intelligently

## Required reasoning modules
The project should gain these modules or their equivalents:

1. `prompt_parser`
   - Extract intent, scene, action, style, continuity constraints

2. `character_state_manager`
   - Canonical state for `<character>`
   - hair, eyes, face, outfit, accessories, forbidden drift

3. `prop_state_manager`
   - room, bed, pillow, phone, ID card, prank props, overlay props

4. `single_panel_planner`
   - Turn prompt into one strict panel spec

5. `multi_panel_planner`
   - Turn prompt/story into ordered panel specs

6. `panel_spec_schema`
   - Structured contract for each panel

7. `execution_planner`
   - Decide stage order: base gen, patch, refine, overlay, export

8. `continuity_evaluator`
   - Check identity, props, scene, eye state, overlay correctness

9. `correction_target_generator`
   - Decide what to patch and where

10. `comic_assembler`
   - Combine final panels into strip/page output

## Required state objects
At minimum the system must support:

### CharacterState
- character_name
- source_series
- canonical_tags
- hair_color
- hairstyle
- eye_color
- face_shape
- outfit_family
- accessories
- must_keep
- forbidden_drift

### PropState
- room_state
- bed_state
- pillow_state
- phone_state
- id_card_state
- prank_state
- recurring_objects

### SceneState
- location
- lighting
- camera defaults
- time of day
- mood

### SinglePanelSpec
- panel_id
- shot_type
- camera_angle
- scene_description
- action_description
- expression
- eye_state
- prop_requirements
- continuity_must_keep
- forbidden_drift
- overlay_plan
- correction_targets

### ComicSequenceSpec
- global_story
- character_state
- prop_state
- scene_state
- ordered_panels
- output_layout

## ComfyUI usage rule
ComfyUI is the **execution engine**, not the planner.

Preferred stage separation:
1. base generation
2. structure/pose control if needed
3. regional eye/face patch
4. prop patch
5. text/overlay render
6. final refine/upscale
7. export

## Detector rule
Use existing YOLO eye/face detectors for:
- eye patch targeting
- face patch targeting
- continuity checks
- regional correction
Do not rely purely on full-frame prompt control for delicate eye placement.

## Character switching rule
The user may change `<character>` frequently across runs.
Within one run:
- resolve `<character>` once
- freeze canonical identity
- reuse it for all panels unless explicitly changed

## Overlay rule
Prefer external overlay rendering for:
- title bars
- phone UI
- ID card text
- speech bubbles
- panel labels

## Evaluation rule
Every generated panel should be checked for:
- identity consistency
- prop continuity
- scene continuity
- eye/tape placement correctness
- overlay correctness
- instruction adherence

If failed:
- patch only what failed
- do not regenerate everything unless required

## Output style for audits and plans
When analyzing the repo, always answer in this format:
- CURRENT STATE
- GAPS
- REQUIRED MODULES
- FILES TO MODIFY
- FILES TO ADD
- PATCH ORDER
- TEST STRATEGY

## Output style for implementation
When writing code, always answer in this format:
- PATCH TARGET
- PURPOSE
- FILE PATH
- CODE
- TEST STEPS
- NEXT ACTION

## Anti-hallucination rule
- Ground every proposal in the current repository structure.
- Prefer exact file/module mapping over abstract ideas.
- State assumptions clearly.
- Do not claim a module exists unless it was actually found.
