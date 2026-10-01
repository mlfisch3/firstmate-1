#!/usr/bin/env python3
"""Externalize captain-kind held backlog items to data/archive/holds/<id>.md
and shorten each hold_reason to a one-line pointer.

Owned by the self-overhaul-archive skill (stage 2).
Idempotent: a second run finds every hold_reason already shortened to the
pointer form and makes no additional changes.
Refuses to run outside a firstmate home that has a data/ directory.
"""
import re
import subprocess
import sys
from pathlib import Path

ARCH = Path("data/archive/holds")
POINTER_PREFIX = "See data/archive/holds/"


def ensure_firstmate_home() -> None:
    if not Path("data").is_dir():
        sys.exit("error: run from a firstmate home root; no data/ directory here")
    ARCH.mkdir(parents=True, exist_ok=True)


def sh(cmd: list[str], check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.stderr}")
    return r.stdout


def list_captain_hold_ids() -> list[str]:
    """IDs of captain-kind held backlog items."""
    out = sh(
        ["tasks-axi", "list", "--state", "held",
         "--fields", "hold_kind", "--limit", "500"]
    )
    ids: list[str] = []
    for line in out.splitlines():
        m = re.match(r"^\s*([a-z0-9][a-z0-9_-]*),queued,captain,", line)
        if m:
            ids.append(m.group(1))
    return ids


def show_field(text: str, name: str) -> str:
    """Parse a `  <name>: <value>` line from tasks-axi show --full output."""
    m = re.search(rf"^  {name}: (.*)$", text, re.MULTILINE)
    if not m:
        return ""
    v = m.group(1)
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    v = v.replace('\\"', '"').replace("\\n", "\n")
    return v


def already_shortened(reason: str, id_: str) -> bool:
    """True when a hold_reason already matches the pointer form for this id."""
    return reason.strip() == f"{POINTER_PREFIX}{id_}.md"


def write_hold_md(id_: str, title: str, repo: str, reason: str) -> Path:
    """Write data/archive/holds/<id>.md with the four durable sections."""
    src_paths = sorted(set(re.findall(r"data/[A-Za-z0-9_./-]+\.md", reason)))
    provenance = ""
    if src_paths:
        provenance = "- Source reports referenced in the Question:\n"
        provenance += "".join(f"  - `{p}`\n" for p in src_paths)

    body = f"""# {title}

- Backlog id: `{id_}`
- Repo: {repo}
- Hold kind: captain

## Question

{reason}

## Notes and recommendations

The Question section carries the analysis, tradeoffs, and any recommendation from the investigation that produced this decision.
Where the text names an option (A/B/C/D) with a "report recommends" line, that is the current standing recommendation.

## Plans-per-option (formulated so far)

No implementation plans have been drafted yet for the options this decision offers.
When the captain answers, a fresh crewmate or scout picks up from here with the answer, this file, and the original report as context.

## Provenance

- Original backlog record: `data/backlog.md` id=`{id_}`
{provenance}- Full backlog body: run `tasks-axi show {id_} --full`
"""
    out = ARCH / f"{id_}.md"
    out.write_text(body)
    return out


def shorten_hold_reason(id_: str) -> None:
    """Rewrite the backlog hold_reason to the one-line archive pointer."""
    subprocess.run(
        ["tasks-axi", "hold", id_, "--reason", f"{POINTER_PREFIX}{id_}.md"],
        capture_output=True,
        check=False,
    )


def externalize(id_: str) -> tuple[Path | None, bool]:
    """Externalize one captain hold.

    Returns (output path or None, whether the item was already fully
    externalized before this run).
    """
    full = sh(["tasks-axi", "show", id_, "--full"])
    title = show_field(full, "title")
    repo = show_field(full, "repo")
    reason = show_field(full, "hold_reason")
    out_path = ARCH / f"{id_}.md"

    if already_shortened(reason, id_) and out_path.exists():
        return (None, True)

    path = write_hold_md(id_, title, repo, reason)
    shorten_hold_reason(id_)
    return (path, False)


def main() -> int:
    ensure_firstmate_home()
    ids = list_captain_hold_ids()
    print(f"found {len(ids)} captain-kind holds", file=sys.stderr)
    written = 0
    unchanged = 0
    for id_ in ids:
        try:
            path, was_idempotent = externalize(id_)
            if was_idempotent:
                unchanged += 1
                continue
            if path is not None:
                print(f"wrote {path}")
                written += 1
        except Exception as e:  # pragma: no cover - surfaces per-item errors
            print(f"warn: {id_}: {e}", file=sys.stderr)
    total = len(list(ARCH.iterdir())) if ARCH.exists() else 0
    print(
        f"\nexternalized {written} new; "
        f"{unchanged} already pointer-form; "
        f"{total} captain-hold MDs total in {ARCH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
