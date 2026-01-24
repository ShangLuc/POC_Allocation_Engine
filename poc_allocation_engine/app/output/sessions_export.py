from __future__ import annotations

from typing import List
import numpy as np

from app.domain.indices import Indexer
from app.domain.variables import ProblemData
from app.schemas.dto import PresentationSession


def export_sessions(
    problem: ProblemData,
    ix: Indexer,
    x: np.ndarray,
) -> List[PresentationSession]:

    sessions: List[PresentationSession] = []

    for p in range(ix.P):
        for t in range(ix.T):
            room = None
            for s in range(ix.S):
                if x[ix.as_index(p, s, t)] > 0.5:
                    room = problem.room_ids[s]
                    break

            if room is None:
                continue

            students = [
                e
                for e in range(ix.E)
                if x[ix.ae_index(e, p, t)] > 0.5
            ]

            sessions.append(
                PresentationSession(
                    presentation_id=problem.presentation_ids[p],
                    room_id=room,
                    slot=t,
                    student_indices=students,
                )
            )

    return sessions
