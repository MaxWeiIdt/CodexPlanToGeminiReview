---
name: gemini-review
description: Review Codex implementation with the configured Gemini review backend, keep the same review session, and write the approval marker only after explicit approval.
---

# Gemini Review

Use this skill after code changes, refactors, config changes, technical documentation changes, batch flow changes, API flow changes, or data processing changes.

Do not use this skill for pure Q&A tasks that do not modify files.

## 1. Review Directory

Use the current project's `.codex/review/` directory as the review state folder.

Required files:

| File | Purpose |
|---|---|
| `.codex/review/enabled` | Opts this project into the Stop Hook review gate |
| `.codex/review/implementation-plan.md` | Records the task goal, changed files, implementation strategy, verification, and risks |
| `.codex/review/gemini-session.json` | Stores the review backend session state, such as `agy_conversation_id` or API interaction id |
| `.codex/review/approval.marker` | Marker checked by the Stop Hook |
| `.codex/review/last-review.md` | Stores the latest review result |

Create `.codex/review/` if it does not exist.

## 2. Reset Rule

Before each review run, reset `.codex/review/approval.marker` to:

```text
[REVIEW_PENDING]
```

Never reuse an old `[REVIEW_APPROVED]` marker from a previous task.

## 3. Implementation Plan

Before running review, create or update:

```text
.codex/review/implementation-plan.md
```

It must include at least:

```md
# Implementation Plan

## Task Goal
Describe what this task is trying to solve.

## Files To Change
List the files planned or already changed.

## Implementation Strategy
Describe the main implementation choices and tradeoffs.

## Verification
List tests, checks, or manual validation performed or planned.

## Risks
List risks to existing behavior, data formats, integrations, or deployment.
```

## 4. Run Review Backend

Run:

```powershell
python "$env:USERPROFILE\.codex\review-scripts\gemini_review.py"
```

The script reads `%USERPROFILE%\.codex\gemini-review.secrets.json` to choose the backend. Supported modes include:

- `agy_cli`: use Antigravity CLI and preserve `agy_conversation_id` in `.codex/review/gemini-session.json`.
- `api`: use Gemini API and preserve API interaction id in `.codex/review/gemini-session.json`.

In `agy_cli` mode, the review script sets the Antigravity subprocess working directory to the current project root, passes `agy --add-dir <project-root>` by default, and asks Antigravity to read `.codex/review/agy-review-prompt.md` by absolute path. This avoids reading stale same-name prompt files from Antigravity scratch directories. If a project must be selected explicitly, set `agy_project` or `project` in `%USERPROFILE%\.codex\gemini-review.secrets.json`; the script will pass it as `agy --project`. If a local Antigravity CLI version does not support `--add-dir`, set `agy_add_dir` to `false` in the same config file.

## 5. Same Session Rule

The review must stay in the same backend session.

- In `agy_cli` mode, reuse `.codex/review/gemini-session.json` field `agy_conversation_id` with `agy --conversation`.
- In `api` mode, reuse `.codex/review/gemini-session.json` field `previous_interaction_id`.
- If the reviewer requests changes, make the changes and review again in the same session.
- Do not delete `gemini-session.json` to bypass earlier review feedback.

### New Session Command

If the user explicitly includes:

```text
[NEW_GEMINI_REVIEW_SESSION]
```

then Codex may start a fresh review session for the current backend. Add the command to `.codex/review/implementation-plan.md`; `gemini_review.py` will clear only the current backend session id before running review:

- `agy_cli`: clears `agy_conversation_id`.
- `api`: clears `previous_interaction_id`.

Do not use this command unless the user explicitly asks for a new Gemini Review session.

## 6. Approval Conditions

Only consider the review approved when all conditions are true:

- The reviewer explicitly approves the implementation.
- The reviewer lists no blocking issue.
- Codex has completed all required review changes.
- Codex has run reasonable verification, or clearly explains why verification could not be run.

After approval, write `.codex/review/approval.marker` with `[REVIEW_APPROVED]` as the final line.

## 7. If Review Fails

If the reviewer returns blocking issues, required changes, or uncertainty, Codex must:

1. Summarize the main feedback.
2. Modify the relevant files.
3. Run necessary verification.
4. Call the review script again.
5. Keep using the same review session.

Do not write `[REVIEW_APPROVED]` until the reviewer explicitly approves.

## 8. Prohibited

- Do not skip review unless the user explicitly uses `[SKIP_GEMINI_REVIEW]` or asks to skip Gemini Review Gate.
- Do not assume the reviewer approved.
- Do not overwrite unresolved review feedback with a new review session.
- Do not write `[REVIEW_APPROVED]` into application source files.
- Do not finish an implementation task without `implementation-plan.md`.
