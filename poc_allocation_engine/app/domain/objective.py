from __future__ import annotations

import numpy as np

from .indices import Indexer
from .variables import ProblemData


def build_objective(problem: ProblemData, ix: Indexer) -> np.ndarray:
    """
    Objective from PDF:

      f_obj,e(ae) = sum_{e,p,t} ae(e,p,t) * [c(e,5) = p]
        (penalize assignments to 5th choice)

      f_obj,s(as) = (1 / (P*S*T + 1)) * sum_{p,s,t} as(p,s,t)
        (secondary objective: minimize number of scheduled presentation occurrences)

    Total objective: minimize f_obj,e + f_obj,s
    """
    n = ix.n_vars()
    c = np.zeros(n, dtype=float)

    # Primary: penalize using 5th choice
    for e in range(ix.E):
        p5 = problem.student_choices.choices[e][4]  # 5th choice index
        for t in range(ix.T):
            c[ix.ae_index(e, p5, t)] += 1.0

    # Secondary: tiny penalty for scheduling many presentation occurrences
    eps = 1.0 / (ix.P * ix.S * ix.T + 1.0)
    for p in range(ix.P):
        for s in range(ix.S):
            for t in range(ix.T):
                c[ix.as_index(p, s, t)] += eps

    return c
