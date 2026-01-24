from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ortools.sat.python import cp_model

from .indices import Indexer
from .variables import ProblemData


@dataclass(frozen=True)
class ConstraintsConfig:
    """
    Knobs to match interpretation/requirements.

    enforce_one_room_per_presentation_per_slot:
      - If True: for each (p,t), sum_s as(p,s,t) <= 1
      - If False: allow a presentation to be split across multiple rooms in same slot (usually undesired)
    """
    enforce_one_room_per_presentation_per_slot: bool = True


def _student_allowed_slots(T: int, wave: int) -> List[int]:
    """
    PDF equations (page with wave constraints) imply:
      - Global slots: 5
      - Wave 1 attends t=1..4 and not t=5
      - Wave 2 attends t=2..5 and not t=1
    Using 0-based indices:
      - Wave 1: [0,1,2,3]
      - Wave 2: [1,2,3,4]
    """
    if T != 5:
        # If you ever decide to use different global slot model, adjust here.
        # For now, we keep the PDF behavior.
        raise ValueError(f"This implementation assumes T=5 global slots. Got T={T}.")
    if wave == 1:
        return [0, 1, 2, 3]
    if wave == 2:
        return [1, 2, 3, 4]
    raise ValueError(f"Invalid wave={wave}. Expected 1 or 2.")


def add_constraints(
    model: cp_model.CpModel,
    vars: Sequence[cp_model.IntVar],
    problem: ProblemData,
    ix: Indexer,
    cfg: ConstraintsConfig,
) -> None:
    """Add all constraints directly to a CP-SAT model."""

    # ---- (C1) Choice 1 must be respected exactly once across time
    for e in range(ix.E):
        p1 = problem.student_choices.choices[e][0]
        model.Add(sum(vars[ix.ae_index(e, p1, t)] for t in range(ix.T)) == 1)

    # ---- (C2) Choice 2 must be respected exactly once across time
    for e in range(ix.E):
        p2 = problem.student_choices.choices[e][1]
        model.Add(sum(vars[ix.ae_index(e, p2, t)] for t in range(ix.T)) == 1)

    # ---- (C3) Student uses only their 5 choices per attended slot
    for e in range(ix.E):
        allowed_slots = _student_allowed_slots(ix.T, problem.student_choices.wave[e])
        choices = problem.student_choices.choices[e]

        for t in allowed_slots:
            model.Add(sum(vars[ix.ae_index(e, p, t)] for p in choices) == 1)

        non_attended = [t for t in range(ix.T) if t not in allowed_slots]
        for t in non_attended:
            model.Add(sum(vars[ix.ae_index(e, p, t)] for p in choices) == 0)

    # ---- (C4) No presentation is attended more than once by the same student
    for e in range(ix.E):
        choices = problem.student_choices.choices[e]
        for p in choices:
            model.Add(sum(vars[ix.ae_index(e, p, t)] for t in range(ix.T)) <= 1)

    # ---- (C5) One presentation at most per room per slot
    for s in range(ix.S):
        for t in range(ix.T):
            model.Add(sum(vars[ix.as_index(p, s, t)] for p in range(ix.P)) <= 1)

    # ---- (C6) Optional: One room at most per presentation per slot
    if cfg.enforce_one_room_per_presentation_per_slot:
        for p in range(ix.P):
            for t in range(ix.T):
                model.Add(sum(vars[ix.as_index(p, s, t)] for s in range(ix.S)) <= 1)

    # ---- (C7) Capacity constraint (also links ae to as)
    capacities = problem.capacities
    for s, cap in enumerate(capacities):
        if cap < 0:
            raise ValueError(f"Negative room capacity for room index {s}: {cap}")

    for p in range(ix.P):
        for t in range(ix.T):
            lhs_students = []
            for e in range(ix.E):
                if p in problem.student_choices.choices[e]:
                    lhs_students.append(vars[ix.ae_index(e, p, t)])

            rhs_capacity = [
                int(capacities[s]) * vars[ix.as_index(p, s, t)]
                for s in range(ix.S)
            ]

            model.Add(sum(lhs_students) <= sum(rhs_capacity))
