from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import numpy as np

from app.domain.indices import Indexer
from app.domain.variables import ProblemData


def export_result_csv(
    problem: ProblemData,
    ix: Indexer,
    x: np.ndarray,
    output_path: str | Path,
) -> Path:
    """Export a flat CSV of student assignments.

    Schema:
        student_index,slot,presentation_id,room_id

    One row per assigned (student, slot).
    """

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[int, int, str, str]] = []

    for e in range(ix.E):
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

                rows.append((e, t, problem.presentation_ids[p], room_id))

    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["student_index", "slot", "presentation_id", "room_id"])
        writer.writerows(rows)

    return out_path
