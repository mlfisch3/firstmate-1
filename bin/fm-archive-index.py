#!/usr/bin/env python3
"""Compose data/archive/INDEX.md from the hold MDs and the secondmate archives.

Owned by the self-overhaul-archive skill (second half of stage 4).
Idempotent: a second run with no changes produces byte-identical output.
Refuses to run outside a firstmate home that has data/archive/.

The per-secondmate scope summary is best-effort: it reads the first non-empty
header-free line of charter.md when present, otherwise prints a placeholder.
A home that wants richer summaries edits them into INDEX.md directly after a
run; this script never overwrites the file when nothing structural changed.
"""
import re
import sys
from pathlib import Path

ROOT = Path("data/archive")
HOLDS = ROOT / "holds"
SECONDS = ROOT / "secondmates"

SECONDMATE_PREFIXES = (
    "appmate", "casemate", "docmate", "hardmate", "regmate", "storemate",
)


def ensure_firstmate_home() -> None:
    if not Path("data").is_dir():
        sys.exit("error: run from a firstmate home root; no data/ directory here")
    if not ROOT.is_dir():
        sys.exit(
            "error: no data/archive/ directory; "
            "run the self-overhaul-archive earlier stages first"
        )


def title_of(md_path: Path) -> str:
    """First `# ` line of a markdown file, falling back to the stem."""
    for line in md_path.read_text().splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem


def secondmate_scope(archive_dir: Path) -> str:
    """One line about what this secondmate covered.

    Reads the first non-empty, non-header line of the archived charter.md if
    present; otherwise returns a placeholder the maintainer can edit.
    """
    charter = archive_dir / "charter.md"
    if charter.exists():
        for line in charter.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("---"):
                continue
            if s.lower().startswith("you are a persistent"):
                continue
            return s[:200]
    return "(scope not recorded; edit this line into INDEX.md if needed)"


def is_secondmate_md(stem: str) -> bool:
    return any(stem.startswith(f"{s}-") for s in SECONDMATE_PREFIXES)


def _preserve_body(body: str, target: Path) -> bool:
    """True when target already carries exactly `body` bytes."""
    if not target.exists():
        return False
    return target.read_text() == body


def compose() -> str:
    lines: list[str] = []
    lines.append("# Archive Index")
    lines.append("")
    lines.append("This is the durable index of archived work products in `data/archive/`.")
    lines.append("Firstmate and crewmates keep only this INDEX and the one-line entries below in working memory.")
    lines.append("")
    lines.append("**How to use it:**")
    lines.append("")
    lines.append("- New request or new work overlaps a line here -> `grep` the referenced file for keywords.")
    lines.append("- No hit -> do not open the file.")
    lines.append("- Hit -> read the surrounding text only, judge whether the full file is needed.")
    lines.append("- Captain asks to revive an item -> open the file fully, follow its Provenance to the underlying reports.")
    lines.append("- Present or future work that contradicts an archived position -> name the contradiction and get the captain's word before proceeding.")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Open captain holds (main backlog)")
    lines.append("")
    lines.append("Each is a backlog item still held for the captain's answer. `hold_reason` in the backlog points here.")
    lines.append("")
    backlog_holds: list[Path] = []
    if HOLDS.exists():
        for md in sorted(HOLDS.glob("*.md")):
            if is_secondmate_md(md.stem):
                continue
            backlog_holds.append(md)
    if not backlog_holds:
        lines.append("No backlog captain holds are archived.")
    for md in backlog_holds:
        rel = md.relative_to(Path("data/archive"))
        lines.append(f"- {title_of(md)} - `data/archive/{rel}`")
    lines.append("")
    lines.append(f"({len(backlog_holds)} backlog captain holds)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Open captain holds (inherited from torn-down secondmates)")
    lines.append("")
    lines.append("Each is a decision the corresponding secondmate had open at teardown.")
    lines.append("Underlying reports are preserved under the named `data/archive/secondmates/<name>/` root.")
    lines.append("")
    by_sm: dict[str, list[Path]] = {}
    if HOLDS.exists():
        for md in sorted(HOLDS.glob("*.md")):
            stem = md.stem
            for s in SECONDMATE_PREFIXES:
                if stem.startswith(f"{s}-"):
                    by_sm.setdefault(s, []).append(md)
                    break
    total_sm_holds = 0
    if not by_sm:
        lines.append("No secondmate captain holds are archived.")
    for sm in sorted(by_sm):
        lines.append(f"### {sm}")
        lines.append("")
        for md in by_sm[sm]:
            rel = md.relative_to(Path("data/archive"))
            lines.append(f"- {title_of(md)} - `data/archive/{rel}`")
            total_sm_holds += 1
        lines.append("")
    lines.append(f"({total_sm_holds} secondmate captain holds across {len(by_sm)} torn-down secondmates)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Reference material (torn-down secondmate homes)")
    lines.append("")
    lines.append("Each entry is the full preserved `data/` tree of a secondmate torn down during a self-overhaul-archive pass.")
    lines.append("Grep the directory for keywords; open a specific `report.md` on hit.")
    lines.append("")
    rendered_any_secondmate = False
    if SECONDS.exists():
        for sm_dir in sorted(SECONDS.iterdir()):
            if not sm_dir.is_dir():
                continue
            rendered_any_secondmate = True
            rel = sm_dir.relative_to(Path("data/archive"))
            scope = secondmate_scope(sm_dir)
            reports = sorted(p.name for p in sm_dir.iterdir() if p.is_dir())
            reports_line = ", ".join(reports) if reports else "(loose files only)"
            lines.append(f"### {sm_dir.name}")
            lines.append("")
            lines.append(f"- **Root:** `data/archive/{rel}/`")
            lines.append(f"- **Scope was:** {scope}")
            lines.append(f"- **Preserved artifacts:** {reports_line}")
            lines.append(f"- **Status log:** `data/archive/{rel}/status.log` (all wake events this secondmate ever emitted)")
            lines.append("")
    if not rendered_any_secondmate:
        lines.append("No secondmate archives are present.")
        lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Provenance of this archive")
    lines.append("")
    lines.append("- Composed by `bin/fm-archive-index.py`, owned by the `self-overhaul-archive` skill.")
    lines.append("- Backlog externalizer: `bin/fm-archive-backlog-holds.py`.")
    lines.append("- Secondmate-status externalizer: `bin/fm-archive-secondmate-holds.sh`.")
    lines.append("- Archival directive sender: `bin/fm-archive-steer.sh`.")
    lines.append("- Rule for working with this archive is in `.agents/skills/self-overhaul-archive/SKILL.md`.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ensure_firstmate_home()
    body = compose()
    out = ROOT / "INDEX.md"
    if _preserve_body(body, out):
        print(f"{out} already up to date ({out.stat().st_size} bytes)")
        return 0
    out.write_text(body)
    print(f"wrote {out} ({out.stat().st_size} bytes, {body.count(chr(10)) + 1} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
