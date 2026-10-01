#!/usr/bin/env bash
# Send the standard self-overhaul-archive directive to each named secondmate
# through bin/fm-send.sh.
#
# Owned by the self-overhaul-archive skill (stage 1).
# The directive text is the sole owner of its shape so every pass sends the
# same instructions.
# A doorbell delivery failure is not an error: the message is durably recorded
# in the target secondmate's inbox and the watcher re-rings on cadence.
# Refuses to run with no arguments or outside a firstmate home.
set -eu

if [ $# -eq 0 ]; then
  cat >&2 <<'USAGE'
usage: fm-archive-steer.sh <secondmate-id>...

Sends the self-overhaul-archive directive to each named secondmate.
The directive asks each secondmate to produce data/archive/findings.md
and data/archive/holds/<key>.md files under its own home before teardown.
USAGE
  exit 2
fi

if [ ! -d data ] || [ ! -d state ]; then
  echo "error: run from a firstmate home root; this cwd has no data/ or state/" >&2
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FM_ROOT=${FM_ROOT_OVERRIDE:-$(cd "$SCRIPT_DIR/.." && pwd)}
FM_HOME=${FM_HOME:-$(pwd)}
export FM_HOME

DIRECTIVE=$(cat <<'EOF'
FIRSTMATE archive-and-teardown directive from captain: produce a durable archive package under your own home's data/archive/ so this domain's work is preserved on disk before you are torn down. Deliverables:

1. data/archive/findings.md - your consolidated findings across all completed investigations, with these three sections:
   - "Findings" - what you concluded, one paragraph per finding, most-important first.
   - "Methods" - how each finding was arrived at (which files, logs, experiments, searches, briefly).
   - "References" - every source cited (repo-relative paths, URLs, standards, dates).

2. For each currently-open captain-hold entry in your status log, one file at data/archive/holds/<key>.md with these four sections:
   - "Question" - the captain hold text as it stands, verbatim.
   - "Notes and recommendations" - your reasoning, your recommended answer where you have one, and the tradeoffs.
   - "Plans-per-option (formulated so far)" - any concrete implementation plans you have drafted for each option the captain might choose. If no plan exists for an option, say so explicitly rather than fabricating one.
   - "Provenance" - which of your data/*.md reports carry the underlying analysis.

3. When both are done, append exactly one status line: `done: archive ready in data/archive/ (<N> findings, <M> holds)` and stop. Do not start any other work. Firstmate will inspect the package and tear you down on that signal.

Rules:
- Do not shorten or delete your existing data/ files. Do not touch anything outside your own home.
- If a captain hold requires a decision only the captain can make, leave the hold open in your status log; the MD file preserves the context for revival.
- Do not commit anything anywhere. This is captain-private state.
- If your findings or your open holds already exist in a form that satisfies this contract (a top-level report with the three sections, hold-per-file structure), point to those existing files from data/archive/findings.md and data/archive/holds/<key>.md rather than rewriting.
EOF
)

sent=0
failed=0
for target in "$@"; do
  if ! [ -f "$FM_HOME/state/$target.meta" ]; then
    echo "warn: no state/$target.meta in this home; skipping $target" >&2
    continue
  fi
  if "$FM_ROOT/bin/fm-send.sh" "$target" "$DIRECTIVE" 2>&1; then
    sent=$((sent + 1))
    printf 'sent to %s\n' "$target"
  else
    failed=$((failed + 1))
    printf 'warn: delivery to %s returned nonzero; the inbox record is durable and the watcher will re-ring\n' "$target" >&2
  fi
done

printf '\narchival directive sent to %s secondmate(s); %s returned warnings\n' "$sent" "$failed"
