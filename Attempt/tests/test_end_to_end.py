from app.domain.variables import ProblemData, StudentChoices
from app.domain.model import build_milp
from app.infrastructure.solver import solve
from app.output.students_export import export_students


def test_student_gets_four_assignments():
    problem = ProblemData(
        presentation_ids=["p1", "p2", "p3", "p4", "p5"],
        room_ids=["r1"],
        capacities=[50],
        student_choices=StudentChoices(
            choices=[[0, 1, 2, 3, 4]],
            wave=[1],
        ),
        T_global=5,
    )

    model = build_milp(problem)
    res = solve(model)

    students = export_students(problem, model.indexer, res.x)

    assert len(students) == 1
    assert len(students[0].assignments) == 4
