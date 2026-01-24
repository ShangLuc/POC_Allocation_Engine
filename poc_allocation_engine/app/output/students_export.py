from __future__ import annotations

from typing import List
import numpy as np

from app.domain.indices import Indexer
from app.domain.variables import ProblemData
from app.schemas.dto import StudentAllocation, SlotAssignment


def export_students(
    problem: ProblemData,
    ix: Indexer,
    x: np.ndarray,
) -> List[StudentAllocation]:

    allocations: List[StudentAllocation] = []

    for e in range(ix.E):
        assignments: List[SlotAssignment] = []

        for t in range(ix.T):
            for p in problem.student_choices.choices[e]:
                idx = ix.ae_index(e, p, t)
                if x[idx] > 0.5:
                    room_id = None
                    for s in range(ix.S):
                        if x[ix.as_index(p, s, t)] > 0.5:
                            room_id = problem.room_ids[s]
                            break

                    if room_id is None:
                        continue

                    assignments.append(
                        SlotAssignment(
                            slot=t,
                            presentation_id=problem.presentation_ids[p],
                            room_id=room_id,
                        )
                    )

        allocations.append(
            StudentAllocation(
                student_index=e,
                assignments=sorted(assignments, key=lambda a: a.slot),
            )
        )

    return allocations
