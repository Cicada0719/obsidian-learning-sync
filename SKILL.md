---
name: obsidian-learning-sync
description: Write beginner-friendly teacher-style learning notes into an Obsidian vault after Codex or another agent completes a task. Use when a user asks to sync core ideas, architecture design, implementation rationale, verification steps, or task retrospectives to Obsidian for learning and review.
---

# Obsidian Learning Sync

Use this skill at the end of a completed task. Create one Obsidian note that teaches the user what happened, why the design works, and how to review or practice the same idea.

Do not record hidden chain-of-thought or raw private reasoning. Convert decisions into public, explainable rationale: goals, constraints, architecture, tradeoffs, changed surfaces, validation, and beginner exercises.

## Workflow

1. Confirm the main task is complete before syncing. Use final task context, changed files, commands run, verification results, and relevant architecture decisions.
2. Resolve the vault path in this order:
   - explicit `--vault` value from the user
   - `OBSIDIAN_VAULT_PATH` environment variable
   - the first discovered Obsidian vault under common user folders, identified by a `.obsidian` directory
   - create a default learning vault at `~/Documents/Obsidian/Codex Learning Vault`
3. Pick the project name from the repository folder, product name, or user-provided name.
4. Draft the note in Chinese by default unless the user asks for another language. Use a patient teacher style suitable for beginners.
5. Use `references/learning-note-template.md` for structure. Keep the note medium-depth by default: roughly 800-1500 Chinese characters for normal tasks.
6. Save the note with `scripts/write_learning_note.py`, then verify the printed JSON paths and inspect the note if needed.

## Note Requirements

Every note should be self-contained enough for a beginner to read later without the original chat. Include:

- what problem was solved
- the plain-language mental model
- the architecture or data-flow map
- important design tradeoffs
- key files, interfaces, commands, or APIs
- how the work was verified
- small practice tasks the user can do next

Use Mermaid only when it clarifies architecture, data flow, state transitions, or module relationships. Avoid decorative diagrams.

## Writing Boundaries

- Do not include raw hidden reasoning, private deliberation, or speculative internal thoughts.
- Do include concise design rationale that can be defended from the visible implementation and results.
- Do not paste large diffs or logs. Summarize them and link file paths when useful.
- If verification failed or was skipped, state that plainly and explain the residual risk.
- If the agent made no code changes, still teach the discovered structure, decision, or debugging path.

## Saving

Prepare the note content in a temporary Markdown file, then run:

```bash
python scripts/write_learning_note.py --project "<project name>" --title "<note title>" --content-file "<temp note.md>"
```

Optional:

```bash
python scripts/write_learning_note.py --vault "<vault path>" --project "<project name>" --title "<note title>" --folder "Codex Learning" --content-file "<temp note.md>"
```

The script writes to:

```text
Codex Learning/<project-name>/<timestamp>-<title-slug>.md
Codex Learning/<project-name>/Index.md
```

It prints JSON with `vault_path`, `vault_source`, `note_path`, `index_path`, and `wikilink`.

