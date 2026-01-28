from __future__ import annotations

import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.infrastructure.csv_reader import load_problem
from app.infrastructure.solver import solve
from app.domain.model import build_milp
from app.domain.constraints import ConstraintsConfig
from app.output.students_export import export_students
from app.output.sessions_export import export_sessions
from app.output.result_csv_export import export_result_csv

router = APIRouter()


@router.post("/solve")
async def solve_allocation(
    students_csv: UploadFile = File(...),
    rooms_csv: UploadFile = File(...),
    time_limit: int | None = None,
):
    try:
        project_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmpdir:
            s_path = os.path.join(tmpdir, "students.csv")
            r_path = os.path.join(tmpdir, "rooms.csv")

            with open(s_path, "wb") as f:
                f.write(await students_csv.read())
            with open(r_path, "wb") as f:
                f.write(await rooms_csv.read())

            problem = load_problem(s_path, r_path)

        milp_model = build_milp(
            problem,
            cfg=ConstraintsConfig(enforce_one_room_per_presentation_per_slot=False),
        )

        res = solve(milp_model, time_limit=time_limit)

        exported_csv = export_result_csv(
            problem,
            milp_model.indexer,
            res.x,
            output_path=project_root / "examples" / "result.csv",
        )

        return {
            "status": "OPTIMAL",
            "objective": float(res.fun),
            "students": export_students(problem, milp_model.indexer, res.x),
            "sessions": export_sessions(problem, milp_model.indexer, res.x),
            "exported_csv": str(exported_csv),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
