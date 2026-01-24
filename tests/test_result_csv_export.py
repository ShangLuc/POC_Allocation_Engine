from __future__ import annotations

from pathlib import Path

from app.domain.model import build_milp
from app.domain.variables import ProblemData, StudentChoices
from app.infrastructure.solver import solve
from app.output.result_csv_export import export_result_csv


def test_export_result_csv_creates_rows(tmp_path: Path):
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

    out_path = export_result_csv(problem, model.indexer, res.x, tmp_path / "result.csv")

    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")

    # header + at least one assignment row
    lines = [l for l in content.splitlines() if l.strip()]
    assert lines[0] == "student_index,slot,presentation_id,room_id"
    assert len(lines) >= 2
