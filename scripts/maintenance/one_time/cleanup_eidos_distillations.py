#!/usr/bin/env python3
"""One-time cleanup of low-quality EIDOS distillations.

Removes tautologies, session-specific playbooks, tool-restating heuristics,
and never-helped-but-contradicted entries. Backup must exist before running.
"""

import re
import sqlite3
import sys

DB_PATH = r"<SPARK_HOME>\eidos.db"

TAUTOLOGY_PATTERNS = [
    "try a different approach", "step back and", "try something else",
    "when repeated", "without progress", "always validate", "always verify",
    "be careful", "consider alternatives", "try another approach",
    "simplify scope", "escalate rather than repeat",
]

GENERIC_SESSION_STARTERS = [
    "start with approach like 'apply taskupdate'",
    "start with approach like 'apply enterplanmode'",
    "start with approach like 'execute: sleep",
    "start with approach like 'execute: cd",
]


def classify(row):
    """Return (should_delete: bool, reason: str) for a distillation row."""
    did = row["distillation_id"]
    s = row["statement"] or ""
    low = s.lower()
    dtype = row["type"]
    helped = int(row["times_helped"] or 0)
    contra = int(row["contradiction_count"] or 0)
    used = int(row["times_used"] or 0)
    retrieved = int(row["times_retrieved"] or 0)

    # 1. Tautologies
    if any(p in low for p in TAUTOLOGY_PATTERNS):
        return True, "tautology"

    # 2. Session-specific playbooks (contain hardcoded paths)
    if dtype == "playbook":
        if "C:" in s or "/Users/" in s or "\\Users\\" in s:
            return True, "path-specific playbook"
        if low.count("taskupdate") >= 2:
            return True, "repeated TaskUpdate playbook"

    # 3. Tool-restating heuristics ("When Read X, try: Inspect X")
    if dtype == "heuristic":
        m = re.match(r"When (\w+) (.+?), try: (\w+) (.+)", s)
        if m:
            _, target1, _, target2 = m.groups()
            t1 = target1.strip().lower().replace("\\", "/").split("/")[-1]
            t2 = target2.strip().lower().replace("\\", "/").split("/")[-1]
            if t1 and t2 and (t1 == t2 or t1.startswith(t2) or t2.startswith(t1)):
                return True, "tool-restating"

    # 4. Never helped AND contradicted more than twice
    if helped == 0 and contra > 2:
        return True, "never-helped + contradicted"

    # 5. Generic session-start heuristics (never retrieved)
    if dtype == "heuristic" and helped == 0 and retrieved == 0 and used == 0:
        if any(p in low for p in GENERIC_SESSION_STARTERS):
            return True, "generic session-start"

    return False, "keep"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT distillation_id, type, statement, times_helped, times_used, "
        "times_retrieved, validation_count, contradiction_count FROM distillations"
    ).fetchall()
    print(f"Before cleanup: {len(rows)} distillations")

    to_delete = {}
    for r in rows:
        should_delete, reason = classify(r)
        if should_delete:
            to_delete[r["distillation_id"]] = reason

    # Report
    reason_counts = {}
    for reason in to_delete.values():
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    print(f"To delete: {len(to_delete)}")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")
    print(f"Keeping: {len(rows) - len(to_delete)}")

    if "--dry-run" in sys.argv:
        print("(dry run, no changes made)")
        return 0

    if to_delete:
        placeholders = ",".join(["?"] * len(to_delete))
        conn.execute(
            f"DELETE FROM distillations WHERE distillation_id IN ({placeholders})",
            list(to_delete.keys()),
        )
        conn.commit()

    remaining = conn.execute("SELECT COUNT(*) FROM distillations").fetchone()[0]
    print(f"After cleanup: {remaining} distillations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

