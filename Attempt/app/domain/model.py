from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from ortools.sat.python import cp_model

from .constraints import ConstraintsConfig, add_constraints
from .indices import Indexer
from .objective import build_objective
from .variables import ProblemData


@dataclass(frozen=True)
class CpSatModel:
    """CP-SAT model (OR-Tools) with variables aligned to Indexer."""

    model: cp_model.CpModel
    vars: Sequence[cp_model.IntVar]
    indexer: Indexer
    objective_scale: int
    c: np.ndarray


def build_cpsat(problem: ProblemData, cfg: ConstraintsConfig | None = None) -> CpSatModel:
    """Build a CP-SAT model from a single CSV instance."""
    if cfg is None:
        cfg = ConstraintsConfig()

    E = len(problem.student_choices.choices)
    P = len(problem.presentation_ids)
    S = len(problem.room_ids)
    T = int(problem.T_global)

    if T != 5:
        # This is a deliberate guard: the PDF constraints for waves imply 5 global slots.
        # If you later decide to compress to 4 slots, change constraints._student_allowed_slots accordingly.
        raise ValueError(f"Expected T_global=5 (per PDF wave constraints). Got {T}.")

    ix = Indexer(E=E, P=P, S=S, T=T)

    model = cp_model.CpModel()
    n = ix.n_vars()
    vars = [model.NewBoolVar(f"x[{i}]") for i in range(n)]

    add_constraints(model, vars, problem, ix, cfg)

    # Keep the original objective coefficient vector for debugging/tests.
    c = build_objective(problem, ix)

    # Objective matches previous MILP objective but as integer/lexicographic:
    # minimize primary (# of 5th-choice assignments) then minimize secondary (# scheduled sessions)
    primary = []
    for e in range(ix.E):
        p5 = problem.student_choices.choices[e][4]
        for t in range(ix.T):
            primary.append(vars[ix.ae_index(e, p5, t)])

    secondary = [vars[ix.as_index(p, s, t)] for p in range(ix.P) for s in range(ix.S) for t in range(ix.T)]
    scale = ix.P * ix.S * ix.T + 1
    model.Minimize(sum(primary) * scale + sum(secondary))

    return CpSatModel(model=model, vars=vars, indexer=ix, objective_scale=scale, c=c)


# Backwards-compatible name used throughout the codebase/tests
def build_milp(problem: ProblemData, cfg: ConstraintsConfig | None = None) -> CpSatModel:
    return build_cpsat(problem, cfg)
