#!/usr/bin/env bash
# Extract each still-open captain hold from each archived secondmate status.log
# into one MD per hold under data/archive/holds/<secondmate>-<key>.md.
#
# Owned by the self-overhaul-archive skill (first half of stage 4).
# Idempotent: a second run finds every target already present and writes
# nothing new.
# Refuses to run outside a firstmate home that has data/archive/secondmates/.
set -eu

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FM_ROOT=${FM_ROOT_OVERRIDE:-$(cd "$SCRIPT_DIR/.." && pwd)}
# shellcheck source=bin/fm-classify-lib.sh
. "$FM_ROOT/bin/fm-classify-lib.sh"

if [ ! -d data/archive/secondmates ]; then
  echo "error: run from a firstmate home that has data/archive/secondmates/" >&2
  echo "run the self-overhaul-archive stage 3 rsync first" >&2
  exit 1
fi

ARCH=data/archive/holds
mkdir -p "$ARCH"

TODAY=$(date -u +%Y-%m-%d)

written=0
unchanged=0

for status in data/archive/secondmates/*/status.log; do
  [ -f "$status" ] || continue
  secondmate=$(basename "$(dirname "$status")")
  # status_open_decisions emits key<TAB>verb<TAB>summary per still-open decision
  while IFS=$'\t' read -r key verb summary; do
    case "$verb" in
      needs-decision|blocked) ;;
      *) continue ;;
    esac
    [ -n "$key" ] || continue
    slug=$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '-')
    out="$ARCH/${secondmate}-${slug}.md"
    if [ -f "$out" ]; then
      unchanged=$((unchanged + 1))
      continue
    fi

    {
      printf '# %s: %s\n\n' "$secondmate" "$key"
      printf -- '- Source secondmate: `%s` (archived on %s)\n' "$secondmate" "$TODAY"
      printf -- '- Hold key: `%s`\n' "$key"
      printf -- '- Verb: `%s`\n' "$verb"
      printf -- '- Archived status log: `data/archive/secondmates/%s/status.log`\n\n' "$secondmate"

      printf '## Question\n\n'
      printf -- '%s\n\n' "$summary"

      printf '## Notes and recommendations\n\n'
      printf 'The Question section carries the analysis, tradeoffs, and any recommendation from the investigation that produced this decision.\n'
      printf 'The full body of the investigation and any supporting reports are preserved under `data/archive/secondmates/%s/` from before teardown.\n\n' "$secondmate"

      printf '## Plans-per-option (formulated so far)\n\n'
      printf 'No implementation plans have been drafted yet for the options this decision offers.\n'
      printf 'On revival, spawn a fresh crewmate or scout with this file plus the underlying reports (see Provenance) as context.\n\n'

      printf '## Provenance\n\n'
      printf -- '- Archived data root: `data/archive/secondmates/%s/`\n' "$secondmate"
      src=$(printf '%s\n' "$summary" | grep -oE 'data/[A-Za-z0-9_./-]+\.md' | sort -u || true)
      if [ -n "$src" ]; then
        printf -- '- Report paths named in the Question (relative to the pre-teardown secondmate home):\n'
        while IFS= read -r p; do
          [ -n "$p" ] && printf -- '  - `%s` -> under `data/archive/secondmates/%s/` becomes `%s`\n' \
            "$p" "$secondmate" "${p#data/}"
        done <<EOF
$src
EOF
      fi
    } > "$out"
    written=$((written + 1))
    printf 'wrote %s\n' "$out"
  done < <(status_open_decisions "$status")
done

printf '\nextracted %s new secondmate captain-hold MDs; %s already present\n' "$written" "$unchanged"
