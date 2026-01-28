from app.domain.variables import ProblemData, StudentChoices
from app.domain.model import build_milp
from app.infrastructure.solver import solve


def test_solver_finds_solution():
    problem = ProblemData(
        presentation_ids=["p1", "p2", "p3", "p4", "p5"],
        room_ids=["r1"],
        capacities=[10],
        student_choices=StudentChoices(
            choices=[[0, 1, 2, 3, 4]],
            wave=[1],
        ),
        T_global=5,
    )

    model = build_milp(problem)
    res = solve(model)

    assert res.success
    assert res.x is not None
    assert len(res.x) == model.indexer.n_vars()
