from __future__ import annotations

import argparse
import os
import sys


# Allow running as: python examples\preprocess_students_all.py
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.infrastructure.student_preprocessor import preprocess_students_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preprocess a global students CSV into 4 disjoint CSV files "
            "(day1/2 x morning/afternoon) with allowed_slots."
        )
    )
    parser.add_argument(
        "--input",
        default=os.path.join("examples", "students_all.csv"),
        help="Path to the global students CSV (default: examples/students_all.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("examples", "students_split"),
        help="Output directory (default: examples/students_split)",
    )
    parser.add_argument(
        "--date-column",
        default="Date",
        help="Name of the date column (default: Date)",
    )
    parser.add_argument(
        "--arrival-time-column",
        default="Heure",
        help="Name of the arrival time column (default: Heure)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a short summary to stdout",
    )

    args = parser.parse_args()

    summary = preprocess_students_csv(
        args.input,
        args.output_dir,
        date_column=args.date_column,
        arrival_time_column=args.arrival_time_column,
    )

    if args.verbose:
        print("Preprocessing complete.")
        print(f"- Input rows: {summary.input_rows}")
        print(f"- Unique students: {summary.unique_students}")
        print(f"- Dates: {', '.join(d.isoformat() for d in summary.dates)}")
        for bucket, path in summary.output_paths.items():
            print(f"- {bucket}: {summary.output_counts[bucket]} rows -> {path}")


if __name__ == "__main__":
    main()
