import numpy as np

from app.domain.variables import ProblemData, StudentChoices
from app.domain.model import build_milp
from app.infrastructure.solver import solve


def minimal_problem():
    return ProblemData(
        presentation_ids=["p1", "p2", "p3", "p4", "p5"],
        room_ids=["r1"],
        capacities=[10],
        student_choices=StudentChoices(
            choices=[[0, 1, 2, 3, 4]],
            wave=[1],
        ),
        T_global=5,
    )


def test_choice_1_and_2_are_hard_constraints():
    problem = minimal_problem()
    model = build_milp(problem)

    res = solve(model)

    # Choice 1 and 2 are hard constraints: each must be scheduled exactly once.
    ix = model.indexer
    p1 = 0
    p2 = 1

    assert sum(res.x[ix.ae_index(0, p1, t)] for t in range(ix.T)) == 1.0
    assert sum(res.x[ix.ae_index(0, p2, t)] for t in range(ix.T)) == 1.0
