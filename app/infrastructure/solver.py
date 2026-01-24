from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ortools.sat.python import cp_model

from app.domain.model import CpSatModel


@dataclass(frozen=True)
class SolveResult:
    success: bool
    status: str
    x: np.ndarray
    fun: float


def solve(model: CpSatModel, time_limit: int | None = None) -> SolveResult:
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = float(time_limit)

    status_code = solver.Solve(model.model)
    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    status = status_map.get(status_code, str(status_code))

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"CP-SAT failed: {status}")

    n = model.indexer.n_vars()
    x = np.zeros(n, dtype=float)
    for i, v in enumerate(model.vars):
        x[i] = float(solver.Value(v))

    # Convert integer lexicographic objective back to the previous float scale:
    # objective = primary + secondary/scale
    objective_int = float(solver.ObjectiveValue())
    fun = objective_int / float(model.objective_scale)

    return SolveResult(success=True, status=status, x=x, fun=fun)
