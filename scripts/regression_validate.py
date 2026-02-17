#!/usr/bin/env python3
"""Regression validation for Pipeline-Driven Analysis Tools refactoring.

Captures baseline analysis snapshots and compares post-refactoring results
to ensure no unintended behavioral changes.

Usage:
    # Capture baseline (run before any code changes)
    python scripts/regression_validate.py baseline

    # Validate after a phase (compares against baseline)
    python scripts/regression_validate.py phase1
    python scripts/regression_validate.py us1
    python scripts/regression_validate.py us2  --expect-name-changes
    python scripts/regression_validate.py us3  --expect-name-changes
    python scripts/regression_validate.py us5  --expect-name-changes

    # Show what baselines exist
    python scripts/regression_validate.py status
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Configuration ---

COLLECTIONS = [
    "col_06jyx7725veb68004pab2s54my",
    "col_06k555trqvfax80033hypdtt2x",
]

TOOLS = ["photostats", "photo_pairing"]

SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "snapshots"

# PhotoStats fields that must match exactly
PHOTOSTATS_STRUCTURAL_KEYS = [
    "total_files",
    "total_size",
    "file_counts",
    "issues_count",
    "issues_found",
    "orphaned_images",
    "orphaned_xmp",
]

# Photo_Pairing fields that must match exactly (structural)
PHOTO_PAIRING_STRUCTURAL_KEYS = [
    "total_files",
    "photo_files",
    "image_count",
    "group_count",
    "invalid_files",
    "invalid_files_count",
]

# Photo_Pairing fields where name changes are expected after US2/US3
PHOTO_PAIRING_NAME_KEYS = [
    "camera_usage",
    "method_usage",
]


def run_tool(
    collection_guid: str, tool: str, snapshot_dir: Path
) -> Tuple[bool, str]:
    """Run a tool with --force --snapshot and return (success, message)."""
    cmd = [
        "shuttersense-agent",
        "run",
        collection_guid,
        "--tool",
        tool,
        "--force",
        "--snapshot",
        str(snapshot_dir),
    ]
    print(f"  Running: {tool} on {collection_guid[:20]}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            return False, f"Exit code {result.returncode}: {result.stderr.strip()}"
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout after 300s"
    except FileNotFoundError:
        return False, "shuttersense-agent not found in PATH"


def load_snapshot(snapshot_dir: Path, tool: str, collection: str) -> Optional[Dict]:
    """Load a snapshot JSON file."""
    path = snapshot_dir / f"{tool}_{collection}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compare_values(key: str, baseline: Any, current: Any) -> Optional[str]:
    """Compare two values and return a diff description or None if equal."""
    if isinstance(baseline, dict) and isinstance(current, dict):
        diffs = []
        all_keys = set(baseline.keys()) | set(current.keys())
        for k in sorted(all_keys):
            if k not in baseline:
                diffs.append(f"  + {key}.{k}: {current[k]}")
            elif k not in current:
                diffs.append(f"  - {key}.{k}: {baseline[k]}")
            elif baseline[k] != current[k]:
                diffs.append(f"  ~ {key}.{k}: {baseline[k]} -> {current[k]}")
        return "\n".join(diffs) if diffs else None
    elif isinstance(baseline, list) and isinstance(current, list):
        if sorted(str(x) for x in baseline) != sorted(str(x) for x in current):
            bl = len(baseline)
            cl = len(current)
            return f"  {key}: list length {bl} -> {cl}" if bl != cl else f"  {key}: list contents differ"
    elif baseline != current:
        return f"  {key}: {baseline} -> {current}"
    return None


def compare_structural(
    tool: str, baseline: Dict, current: Dict
) -> List[str]:
    """Compare structural fields that must match exactly."""
    keys = (
        PHOTOSTATS_STRUCTURAL_KEYS
        if tool == "photostats"
        else PHOTO_PAIRING_STRUCTURAL_KEYS
    )
    diffs = []
    for key in keys:
        if key not in baseline and key not in current:
            continue
        b_val = baseline.get(key)
        c_val = current.get(key)
        diff = compare_values(key, b_val, c_val)
        if diff:
            diffs.append(diff)
    return diffs


def compare_names(baseline: Dict, current: Dict) -> List[str]:
    """Compare name-resolution fields (camera_usage, method_usage)."""
    diffs = []
    for key in PHOTO_PAIRING_NAME_KEYS:
        if key not in baseline and key not in current:
            continue
        b_val = baseline.get(key, {})
        c_val = current.get(key, {})
        diff = compare_values(key, b_val, c_val)
        if diff:
            diffs.append(diff)
    return diffs


def capture_baseline() -> bool:
    """Run all tools on all collections and save baseline snapshots."""
    baseline_dir = SNAPSHOT_ROOT / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("CAPTURING BASELINE SNAPSHOTS")
    print("=" * 60)

    all_ok = True
    for col in COLLECTIONS:
        for tool in TOOLS:
            ok, msg = run_tool(col, tool, baseline_dir)
            if not ok:
                print(f"    FAIL: {msg}")
                all_ok = False
            else:
                # Verify snapshot was created
                snap = load_snapshot(baseline_dir, tool, col)
                if snap is None:
                    print(f"    FAIL: Snapshot file not created")
                    all_ok = False
                else:
                    files = snap.get("total_files") or snap.get("files_scanned") or "?"
                    print(f"    OK ({files} files)")

    if all_ok:
        print()
        print(f"Baseline saved to: {baseline_dir}")
        print(f"Snapshots: {len(list(baseline_dir.glob('*.json')))} files")
    else:
        print()
        print("BASELINE CAPTURE FAILED — fix errors above before proceeding")
    return all_ok


def validate_phase(phase: str, expect_name_changes: bool) -> bool:
    """Run all tools and compare against baseline."""
    baseline_dir = SNAPSHOT_ROOT / "baseline"
    phase_dir = SNAPSHOT_ROOT / phase

    if not baseline_dir.exists():
        print("ERROR: No baseline found. Run 'baseline' first.")
        return False

    phase_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"VALIDATING PHASE: {phase}")
    if expect_name_changes:
        print("  (name-resolution changes expected)")
    print("=" * 60)

    all_ok = True
    structural_pass = 0
    structural_fail = 0
    name_deltas = 0

    for col in COLLECTIONS:
        print(f"\nCollection: {col[:20]}...")
        for tool in TOOLS:
            # Run the tool
            ok, msg = run_tool(col, tool, phase_dir)
            if not ok:
                print(f"  {tool}: RUN FAILED - {msg}")
                all_ok = False
                structural_fail += 1
                continue

            # Load snapshots
            baseline = load_snapshot(baseline_dir, tool, col)
            current = load_snapshot(phase_dir, tool, col)

            if baseline is None:
                print(f"  {tool}: NO BASELINE - skipped")
                structural_fail += 1
                continue
            if current is None:
                print(f"  {tool}: NO SNAPSHOT - run failed silently")
                structural_fail += 1
                all_ok = False
                continue

            # Structural comparison (must always match)
            struct_diffs = compare_structural(tool, baseline, current)
            if struct_diffs:
                print(f"  {tool}: STRUCTURAL MISMATCH")
                for d in struct_diffs:
                    print(f"    {d}")
                all_ok = False
                structural_fail += 1
            else:
                print(f"  {tool}: structural OK", end="")
                structural_pass += 1

                # Name comparison (for photo_pairing only)
                if tool == "photo_pairing":
                    name_diffs = compare_names(baseline, current)
                    if name_diffs:
                        name_deltas += 1
                        if expect_name_changes:
                            print(" | names: expected delta")
                            for d in name_diffs:
                                print(f"      {d}")
                        else:
                            print(" | names: UNEXPECTED CHANGE")
                            for d in name_diffs:
                                print(f"      {d}")
                            all_ok = False
                    else:
                        print(" | names: identical")
                else:
                    print()

    print()
    print("-" * 60)
    print(f"Structural: {structural_pass} passed, {structural_fail} failed")
    if name_deltas:
        print(f"Name deltas: {name_deltas} (expected={expect_name_changes})")
    print(f"Overall: {'PASS' if all_ok else 'FAIL'}")
    print("-" * 60)

    return all_ok


def show_status():
    """Show what snapshots exist."""
    print("Snapshot directory:", SNAPSHOT_ROOT)
    if not SNAPSHOT_ROOT.exists():
        print("  (not created yet)")
        return

    for phase_dir in sorted(SNAPSHOT_ROOT.iterdir()):
        if phase_dir.is_dir():
            files = list(phase_dir.glob("*.json"))
            print(f"  {phase_dir.name}/: {len(files)} snapshots")
            for f in sorted(files):
                data = json.loads(f.read_text(encoding="utf-8"))
                total = data.get("total_files") or data.get("files_scanned") or "?"
                print(f"    {f.name} ({total} files)")


def main():
    parser = argparse.ArgumentParser(
        description="Regression validation for Pipeline-Driven Analysis Tools"
    )
    parser.add_argument(
        "phase",
        help="Phase to validate: baseline, phase1, us1, us2, us3, us5, status",
    )
    parser.add_argument(
        "--expect-name-changes",
        action="store_true",
        help="Allow name-resolution changes in photo_pairing (camera_usage, method_usage)",
    )
    args = parser.parse_args()

    if args.phase == "status":
        show_status()
        sys.exit(0)

    if args.phase == "baseline":
        ok = capture_baseline()
        sys.exit(0 if ok else 1)

    ok = validate_phase(args.phase, args.expect_name_changes)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
