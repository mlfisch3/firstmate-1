#!/usr/bin/env python3
"""Behavior tests for bin/fm-archive-index.py.

Verifies the index composer renders every required section with the right
empty-state wording when nothing is archived, and is idempotent across runs.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "fm-archive-index.py"


def run_script(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def case_refuses_without_data_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        r = run_script(Path(td))
        if r.returncode == 0:
            fail("case_refuses_without_data_dir: expected nonzero exit")
        if "run from a firstmate home" not in r.stderr:
            fail(f"case_refuses_without_data_dir: wrong diag: {r.stderr!r}")
    print("ok - refuses outside a firstmate home")


def case_refuses_without_archive_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "data").mkdir()
        r = run_script(Path(td))
        if r.returncode == 0:
            fail("case_refuses_without_archive_dir: expected nonzero exit")
        if "no data/archive/" not in r.stderr:
            fail(f"case_refuses_without_archive_dir: wrong diag: {r.stderr!r}")
    print("ok - refuses without data/archive/")


def case_empty_archive_renders_all_sections() -> None:
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        (home / "data" / "archive").mkdir(parents=True)
        r = run_script(home)
        if r.returncode != 0:
            fail(f"case_empty_archive: exit {r.returncode}: {r.stderr}")
        idx = (home / "data" / "archive" / "INDEX.md").read_text()
        required_headings = [
            "# Archive Index",
            "## Open captain holds (main backlog)",
            "## Open captain holds (inherited from torn-down secondmates)",
            "## Reference material (torn-down secondmate homes)",
            "## Provenance of this archive",
        ]
        for h in required_headings:
            if h not in idx:
                fail(f"case_empty_archive: missing heading {h!r}")
        empty_states = [
            "No backlog captain holds are archived.",
            "No secondmate captain holds are archived.",
            "No secondmate archives are present.",
        ]
        for es in empty_states:
            if es not in idx:
                fail(f"case_empty_archive: missing empty state {es!r}")
    print("ok - empty archive renders all sections with empty-state wording")


def case_idempotent_second_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        holds = home / "data" / "archive" / "holds"
        holds.mkdir(parents=True)
        (holds / "demo-decision.md").write_text(
            "# Demo decision\n\n## Question\n\nDemo?\n"
        )
        sm = home / "data" / "archive" / "secondmates" / "demomate"
        sm.mkdir(parents=True)
        (sm / "charter.md").write_text(
            "---\nname: demomate\n---\n\n# demomate\n\n"
            "Demo scope for the demonstration mate.\n"
        )
        (sm / "status.log").write_text("done: demo\n")
        r1 = run_script(home)
        if r1.returncode != 0:
            fail(f"case_idempotent: first run failed: {r1.stderr}")
        first = (home / "data" / "archive" / "INDEX.md").read_bytes()
        mtime_first = (home / "data" / "archive" / "INDEX.md").stat().st_mtime
        # Second run with no changes should preserve the existing file.
        os.utime(home / "data" / "archive" / "INDEX.md", (0, mtime_first - 10))
        pinned_mtime = (home / "data" / "archive" / "INDEX.md").stat().st_mtime
        r2 = run_script(home)
        if r2.returncode != 0:
            fail(f"case_idempotent: second run failed: {r2.stderr}")
        second = (home / "data" / "archive" / "INDEX.md").read_bytes()
        if first != second:
            fail("case_idempotent: second run changed INDEX.md bytes")
        mtime_second = (home / "data" / "archive" / "INDEX.md").stat().st_mtime
        if mtime_second != pinned_mtime:
            fail(
                "case_idempotent: second run rewrote INDEX.md "
                f"(mtime {pinned_mtime} -> {mtime_second})"
            )
        if "already up to date" not in r2.stdout:
            fail(
                "case_idempotent: second run did not report already-up-to-date: "
                f"{r2.stdout!r}"
            )
    print("ok - second run is a no-op when nothing changed")


def main() -> int:
    if not SCRIPT.is_file():
        fail(f"script not found: {SCRIPT}")
    case_refuses_without_data_dir()
    case_refuses_without_archive_dir()
    case_empty_archive_renders_all_sections()
    case_idempotent_second_run()
    print("# PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
