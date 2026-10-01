---
name: self-overhaul-archive
description: >-
  Agent-only procedure for a one-off token-reduction self-overhaul of a bloated firstmate home, plus the recurring maintenance rule the archive imposes on every later session.
  Load when the captain says "reduce tokens", "archive the long-idle work", or similar; when a session-start digest shows 20+ long-idle secondmates, 30+ captain-held backlog items whose hold_reason bodies exceed roughly 400 characters each, or a backlog listing whose hold_reason content alone exceeds roughly 30 KB; or whenever a `data/archive/INDEX.md` is already present in this home.
user-invocable: false
metadata:
  internal: true
---

# Self-overhaul archive

A firstmate home accumulates two kinds of long-idle weight that bloat every session start: unanswered captain-held backlog items whose multi-hundred-character `hold_reason` bodies ship in the digest every time, and persistent secondmates whose finished investigations and still-open captain decisions sit in each secondmate's status log and child data tree.

This skill owns one periodic archival pass that moves both kinds of content to captain-private per-item markdown files under `data/archive/`, shortens the backlog `hold_reason` to a one-line pointer, tears down secondmates whose work is preserved, and then imposes a recurring maintenance rule on this home so later sessions carry only a one-line entry per archived item in working memory.

## Captain-private output boundary

Everything the overhaul writes lives under this home's `data/archive/`, which is already captain-private and gitignored.
The skill itself is tracked firstmate material; the per-home archive it produces is not.
Nothing the overhaul generates ever ships through a project or firstmate PR.

## Recurring maintenance rule (always-loaded after the first overhaul)

Once a home has an `data/archive/INDEX.md`, this rule binds every firstmate and crewmate session in that home:

- Load `data/archive/INDEX.md` at session start when present.
  The session-start digest's captain-file sweep already prints it under its ordinary read-once contract when it exists; treat it as part of that read, not an extra fetch.
- Keep only the one-line entry plus the referenced markdown filename per archived item in working memory.
  Never carry the per-item markdown body unless this turn is reviving that specific item.
- When a new request or new work overlaps a line in the index, `grep` the referenced markdown file for keywords.
  On no hit, do not open the file.
  On a hit, read the surrounding lines only, judge whether the whole file is needed.
- When the captain asks to revive an archived item, open the full markdown file, follow its `Provenance` section to the underlying reports preserved under `data/archive/secondmates/<name>/`, and spawn a fresh crewmate or scout with that content as the brief.
- Present or future work that contradicts an archived position names the contradiction and gets the captain's word before proceeding.
  Do not silently supersede an archived decision.

The rule exists so the archive is a net saver on every session that follows the overhaul, not a parallel pile of documents nobody reads.

## When to run the overhaul

Trigger on any of:

- The captain explicitly asks for an archive-and-teardown pass, says "reduce tokens", or describes the current state as bloated.
- The session-start digest in a home shows 20 or more long-idle secondmates in `data/secondmates.md`, with no live work and no recent routed activity.
- The structured backlog carries 30 or more captain-held items whose `hold_reason` bodies each exceed roughly 400 characters, so the digest's compact backlog listing itself exceeds roughly 30 KB from `hold_reason` content alone.

A home that already carries `data/archive/INDEX.md` and whose backlog `hold_reason` fields are already pointers is not a candidate: load the recurring maintenance rule above instead and leave the archive alone.

## Before starting: three decisions

Before running any script, present the captain with three questions and wait for the answers.
The questions are stable because every pass of the overhaul faces the same three forks:

1. Include the main-home captain-held backlog items in this pass, or only the secondmate work.
   Including the backlog shrinks the session-start digest materially; excluding it keeps the pass narrow.
2. Have each secondmate write its own archive package before teardown, or have main firstmate read each secondmate's `data/` tree directly and compose the markdown centrally.
   The first is faithful but costs a burst of activity in six to twelve secondmate homes; the second is single-threaded and dependent on main firstmate's judgment about what a given secondmate's reports really meant.
3. Add the recurring maintenance rule to this home's `data/captain.md` as a durable preference, or rely on the skill alone each session.
   The preference entry is a cheap durable reminder that survives harness-memory loss and is read on every session start.

The three questions are deliberately coarse because the right answer depends on the current fleet shape.
A home with no live secondmates skips question 2 as moot.

## Procedure

The overhaul runs in four stages against the home's live state.
Each stage uses only tracked scripts whose idempotence is tested, so a stage can be re-run after an interruption without duplicating output.

### Stage 1: dispatch the archival steer to live secondmates (optional, question 2 answer A)

When question 2 answered A, each live secondmate must produce its own archive package first.
Send the standard archival directive through `bin/fm-archive-steer.sh`, which is the single owner of the directive text so the shape is stable across runs.

`bin/fm-archive-steer.sh <secondmate-id>...` sends a durable steering-inbox record through `bin/fm-send.sh` with the directive asking that secondmate to write `data/archive/findings.md` and `data/archive/holds/<key>.md` files under its own home.
A doorbell failure is not an error because the message is durable; the watcher re-rings an unacknowledged message on its ordinary cadence.

Wait for each secondmate's `done:` status reporting its archive ready.
A silent or unresponsive secondmate falls back to the question-2-answer-B path for just that secondmate: main firstmate rsyncs its whole `data/` tree during stage 3 and composes nothing centrally.

### Stage 2: externalize main-backlog captain holds (optional, question 1 answer "include")

When question 1 answered include-backlog, run `bin/fm-archive-backlog-holds.py` once from the main home.
The script lists `tasks-axi list --state held --fields hold_kind` for captain-kind rows, writes `data/archive/holds/<id>.md` per item with the four durable sections documented below, and shortens each item's `hold_reason` to `See data/archive/holds/<id>.md` via `tasks-axi hold <id> --reason` so the compact backlog listing in future session-start digests drops to one line per hold.

Re-running the script is a no-op on items whose `hold_reason` already matches the pointer.

### Stage 3: rsync each secondmate's data tree and tear it down

For each secondmate in `data/secondmates.md`, run `rsync -a --exclude='.git' <secondmate-home>/data/ data/archive/secondmates/<name>/` from the main home, copy the secondmate's `state/<name>.status` log into the same destination as `status.log`, verify the destination, then call `bin/fm-teardown.sh <name>` to release the lease, clear registry and state, and remove the secondmate home.
`secondmate-provisioning` owns the retirement safety contract and is loaded here before each teardown.

A secondmate whose work the captain plans to revive within days is not a candidate for teardown; leave it alone and move on.

### Stage 4: extract secondmate captain holds and compose the index

Run `bin/fm-archive-secondmate-holds.sh` from the main home.
It walks each `data/archive/secondmates/*/status.log`, uses `bin/fm-classify-lib.sh`'s `status_open_decisions` fold to find still-open captain holds, and writes `data/archive/holds/<secondmate>-<key>.md` with the same four durable sections, idempotent on re-run.

Then run `bin/fm-archive-index.py` to compose `data/archive/INDEX.md` from the holds directory and the secondmate archives.
The index groups entries as "Open captain holds (main backlog)", "Open captain holds (inherited from torn-down secondmates)", and "Reference material (torn-down secondmate homes)".
Each row is a single line: the item's title plus its markdown filename, nothing else.
Resolved or superseded items move to `data/archive/holds/resolved/` and the index generator skips that subdirectory, so a captain hold answered later stays preserved on disk without reappearing in the index.

### Stage 5: codify the recurring rule (optional, question 3 answer "yes")

When question 3 answered yes, append the recurring-maintenance-rule paragraph to this home's `data/captain.md` under a dated section such as `## Archived work products and the revive-from-MD pattern (YYYY-MM-DD)`.
The paragraph names the per-session grep-before-open rule, the per-item markdown shape, and the revival-from-markdown handoff.
Future firstmate sessions in this home read `data/captain.md` at session start and inherit the rule.

## Per-item markdown shape

Every file under `data/archive/holds/<id>.md` carries exactly four sections, in order:

1. `## Question` - the hold's text verbatim, no editorialization.
2. `## Notes and recommendations` - the reasoning that led to the hold and any report-recommended answer.
3. `## Plans-per-option (formulated so far)` - any concrete implementation plan drafted for each option the captain might choose; when none, say so plainly rather than fabricating one.
4. `## Provenance` - the backlog id or source status log, every source report path mentioned in the question, and the exact `tasks-axi show <id> --full` command to retrieve the full backlog body on revival.

The four-section contract is what makes a markdown file resumable by a fresh crewmate without reading any other archive artifact.

## Per-secondmate archive shape

`data/archive/secondmates/<name>/` carries a verbatim copy of that secondmate's pre-teardown `data/` tree plus a `status.log` copied from the main home's `state/<name>.status`.
Paths inside the secondmate's own reports are relative to the pre-teardown secondmate home, so a reader opening a report under `data/archive/secondmates/<name>/<report>/report.md` treats sibling paths as relative to that report's directory.

A separately composed `data/archive/secondmates/<name>/findings.md` is optional and only exists when the secondmate wrote one during stage 1.
Absence of a findings file is not an error; the preserved reports are themselves the record.

## Scripts and ownership

Each `bin/fm-archive-*` script is the one owner of its stage's mechanics; the skill never inlines what a script already does.
Each script's header owns its exact command surface and refuses to run outside the main firstmate home.

- `bin/fm-archive-backlog-holds.py` owns stage 2.
- `bin/fm-archive-secondmate-holds.sh` owns the first half of stage 4.
- `bin/fm-archive-index.py` owns the second half of stage 4.
- `bin/fm-archive-steer.sh` owns the directive text and stage 1 delivery.

Idempotence is tested per script.
A stage interrupted mid-run is safely re-runnable; no stage uses captain time or captain attention beyond the three up-front questions.
