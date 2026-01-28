from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Allow running as: python examples\solve_students_split.py
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.domain.model import build_milp
from app.infrastructure.csv_reader import _norm_header, _open_csv_text_with_fallback, _sniff_dialect, load_problem
from app.infrastructure.solver import solve


def _pick_student_id_column(header: List[str]) -> int:
    norm = [_norm_header(h) for h in header]
    idx_by_norm: Dict[str, int] = {h: i for i, h in enumerate(norm) if h}

    for key in ("id national", "id eleve", "id élève", "student id", "id"):
        if key in idx_by_norm:
            return idx_by_norm[key]

    # Fallback: first header containing 'id'
    for i, h in enumerate(norm):
        if "id" in h.split():
            return i

    raise ValueError("Could not find a student id column (expected 'ID National' or similar).")


def _read_student_ids_in_order(students_csv: str) -> Tuple[List[str], str]:
    """Return (student_ids, delimiter) in the exact row order used by read_students_csv."""
    student_ids: List[str] = []

    with _open_csv_text_with_fallback(students_csv) as (f, sample):
        dialect = _sniff_dialect(sample)
        reader = csv.reader(f, dialect=dialect) if dialect else csv.reader(f)

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Empty students CSV (no header).")

        if not header:
            raise ValueError("Empty students CSV (no header).")

        id_idx = _pick_student_id_column(header)

        for row in reader:
            if not row or all(str(x).strip() == "" for x in row):
                continue
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))

            sid = (row[id_idx] if id_idx < len(row) else "").strip()
            if sid == "":
                raise ValueError("Missing student id in students CSV.")
            student_ids.append(sid)

        delimiter = getattr(dialect, "delimiter", ",") if dialect else ","
        return student_ids, delimiter


def solve_one(students_csv: Path, rooms_csv: Path, out_csv: Path, *, time_limit: int | None) -> None:
    problem = load_problem(str(students_csv), str(rooms_csv), T_global=5)
    model = build_milp(problem)
    res = solve(model, time_limit=time_limit)

    student_ids, _ = _read_student_ids_in_order(str(students_csv))
    if len(student_ids) != len(problem.student_choices.choices):
        raise ValueError(
            f"Student id count mismatch for {students_csv.name}: "
            f"ids={len(student_ids)} vs parsed={len(problem.student_choices.choices)}"
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Write result with student_id included.
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "student_index", "slot", "presentation_id", "room_id"])

        ix = model.indexer
        x = res.x
        for e in range(ix.E):
            sid = student_ids[e]
            for t in range(ix.T):
                for p in problem.student_choices.choices[e]:
                    if x[ix.ae_index(e, p, t)] <= 0.5:
                        continue

                    room_id: str | None = None
                    for s in range(ix.S):
                        if x[ix.as_index(p, s, t)] > 0.5:
                            room_id = problem.room_ids[s]
                            break

                    if room_id is None:
                        continue

                    w.writerow([sid, e, t, problem.presentation_ids[p], room_id])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the solver on each CSV in a students_split directory, one at a time, "
            "writing one result CSV per input into students_alloc."
        )
    )
    parser.add_argument(
        "--split-dir",
        default=os.path.join("examples", "students_split"),
        help="Directory containing day*_*.csv files (default: examples/students_split)",
    )
    parser.add_argument(
        "--rooms",
        default=os.path.join("examples", "rooms.csv"),
        help="Rooms CSV path (default: examples/rooms.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("examples", "students_alloc"),
        help="Output directory (default: examples/students_alloc)",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=20,
        help="CP-SAT time limit in seconds for each run (default: 20)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress while processing files",
    )

    args = parser.parse_args()

    split_dir = Path(args.split_dir)
    rooms_csv = Path(args.rooms)
    output_dir = Path(args.output_dir)

    if not split_dir.exists() or not split_dir.is_dir():
        raise SystemExit(f"split-dir not found: {split_dir}")
    if not rooms_csv.exists():
        raise SystemExit(f"rooms CSV not found: {rooms_csv}")

    # Process in deterministic order.
    inputs = sorted(p for p in split_dir.glob("*.csv") if p.is_file())
    if not inputs:
        raise SystemExit(f"No CSV files found in: {split_dir}")

    for inp in inputs:
        out_name = f"{inp.stem}_result.csv"
        out_path = output_dir / out_name
        if args.verbose:
            print(f"Solving {inp.name} -> {out_path}")

        solve_one(inp, rooms_csv, out_path, time_limit=args.time_limit)

    if args.verbose:
        print("Done.")


if __name__ == "__main__":
    main()
