# Project Intelligence Loop

This document explains how project-level knowledge flows into Spark's learning,
prediction, and outcome validation loops.

## Why this exists
Tool telemetry (bash/edit/write) captures *how* we act, but not *why* or *when a
project is truly done*. Project intelligence captures:
- Definition of done
- Milestones and phase
- Decisions + rationale
- Domain insights and feedback

## Data model (lightweight)
Project profile is stored in:
`~/.spark/projects/<project_key>.json`

Key fields:
- `domain` (game_dev, marketing, org, product, engineering)
- `phase` (discovery/prototype/polish/launch)
- `done` + `done_history`
- `milestones` (with status)
- `decisions`, `insights`, `feedback`, `risks`
- `questions` + `answers`

## Flow overview
1) **Questioning**
   - `spark project init` seeds domain questions.
   - `spark project questions` shows unanswered + dynamic questions.
   - Domain questions include references + transferable heuristics.

2) **Capture**
   - `spark project capture` records insights, milestones, done criteria, etc.
   - Entries are saved to the project profile and stored in project memory.
   - Use `--type reference` to capture real-world examples.
   - Use `--type transfer` to capture cross-project heuristics.
   - Capturing a reference auto-prompts a transfer check-in.

3) **Prediction**
   - `prediction_loop` generates project predictions from:
     - `done` criteria
     - `milestones` not marked done
   - Predictions include `project_key` and `entity_id`.

4) **Outcomes**
   - `project capture --type done` or `milestone --status done` emits outcomes.
   - Outcomes include `entity_id`, so matching is deterministic.

5) **Context**
   - `sync-context` and `bridge` inject a **Project Focus** block:
     - phase, done criteria, top milestones, goals
   - This ensures domain intelligence outweighs tool telemetry.
6) **Promotion**
   - `spark promote` writes a `PROJECT.md` block from the project profile.
   - This keeps human-readable project intelligence close to the repo.
   - If 3+ transfers exist, a short transfer summary is added.

## Cross-project learning
Project entries are stored in memory banks by category:
- `project_goal`, `project_done`, `project_milestone`
- `project_decision`, `project_insight`
- `project_feedback`, `project_risk`

This allows retrieval across projects and domains while keeping project scope.

## Example
```bash
spark project init --domain game_dev
spark project answer game_core_loop --text "Core loop is satisfying at 60% grab success."
spark project capture --type insight --text "Grip strength vs weight balance matters"
spark project capture --type done --text "Game feels complete when core loop is satisfying"
```

Outcome validation now has concrete, domain-level targets.
