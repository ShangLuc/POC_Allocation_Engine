from __future__ import annotations

from pathlib import Path
import csv

from app.domain.model import build_milp
from app.domain.variables import ProblemData, StudentChoices
from app.infrastructure.csv_reader import load_problem
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


def _allowed_slots(T_global: int, wave: int) -> list[int]:
    # Mirrors domain wave rules in app.domain.constraints._student_allowed_slots
    if T_global != 5:
        raise ValueError("tests assume T_global=5")
    if wave == 1:
        return [0, 1, 2, 3]
    if wave == 2:
        return [1, 2, 3, 4]
    raise ValueError(f"invalid wave={wave}")


def _read_result_rows(path: Path) -> list[tuple[int, int, str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected = {"student_index", "slot", "presentation_id", "room_id"}
        if set(reader.fieldnames or []) != expected:
            raise AssertionError(f"Unexpected result.csv schema: {reader.fieldnames}")
        rows: list[tuple[int, int, str, str]] = []
        for r in reader:
            rows.append((int(r["student_index"]), int(r["slot"]), r["presentation_id"], r["room_id"]))
    return rows


def test_exported_result_csv_is_credible_on_examples_sample(tmp_path: Path):
    """Credibility tests on a small sample of the real example inputs.

    We don't assert optimality here; we assert feasibility invariants:
    - per-student: exactly one assignment per attended slot, none otherwise
    - per-student: assignments only from the student's 5 choices
    - per-student: choice #1 and #2 are respected exactly once
    - per-room per-slot: capacity not exceeded and at most one presentation
    - per-presentation per-slot: at most one room
    """

    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples"
    src_students = examples_dir / "students_choices.csv"
    src_rooms = examples_dir / "rooms.csv"

    # Build a smaller students CSV to keep tests fast.
    sample_students = tmp_path / "students_choices_sample.csv"
    max_students = 60
    with src_students.open("r", encoding="utf-8", newline="") as fin, sample_students.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        for i, line in enumerate(fin):
            fout.write(line)
            # i=0 is header; keep next max_students lines
            if i >= max_students:
                break

    problem = load_problem(str(sample_students), str(src_rooms), T_global=5)
    model = build_milp(problem)
    res = solve(model, time_limit=10)

    out_path = export_result_csv(problem, model.indexer, res.x, tmp_path / "result.csv")
    rows = _read_result_rows(out_path)

    # ---- basic row sanity
    assert rows, "result.csv should not be empty"
    by_student: dict[int, list[tuple[int, str, str]]] = {}
    for e, t, pres_id, room_id in rows:
        assert 0 <= e < len(problem.student_choices.choices)
        assert 0 <= t < int(problem.T_global)
        assert pres_id in set(problem.presentation_ids)
        assert room_id in set(problem.room_ids)
        by_student.setdefault(e, []).append((t, pres_id, room_id))

    # ---- per-student constraints / choices respected
    pid_to_index = {pid: i for i, pid in enumerate(problem.presentation_ids)}

    for e, choices in enumerate(problem.student_choices.choices):
        wave = problem.student_choices.wave[e]
        allowed = set(_allowed_slots(problem.T_global, wave))

        assigned = by_student.get(e, [])
        assigned_slots = [t for (t, _, _) in assigned]
        assert len(assigned_slots) == len(set(assigned_slots)), "duplicate slot for student"

        # exactly one assignment per attended slot
        assert set(assigned_slots) == allowed

        assigned_p_idxs = [pid_to_index[pid] for (_, pid, _) in assigned]

        # only from the student's 5 choices
        assert set(assigned_p_idxs).issubset(set(choices))

        # no presentation attended twice by the same student
        assert len(assigned_p_idxs) == len(set(assigned_p_idxs))

        # choice #1 and #2 respected exactly once across time
        p1, p2 = choices[0], choices[1]
        assert assigned_p_idxs.count(p1) == 1
        assert assigned_p_idxs.count(p2) == 1

    # ---- capacity and room/presentation consistency
    capacity_by_room = {rid: int(problem.capacities[i]) for i, rid in enumerate(problem.room_ids)}
    students_in_room_slot: dict[tuple[str, int], list[tuple[int, str]]] = {}
    rooms_for_pres_slot: dict[tuple[str, int], set[str]] = {}
    pres_for_room_slot: dict[tuple[str, int], set[str]] = {}

    for e, t, pres_id, room_id in rows:
        students_in_room_slot.setdefault((room_id, t), []).append((e, pres_id))
        rooms_for_pres_slot.setdefault((pres_id, t), set()).add(room_id)
        pres_for_room_slot.setdefault((room_id, t), set()).add(pres_id)

    for (room_id, t), students in students_in_room_slot.items():
        assert len(students) <= capacity_by_room[room_id]

    # at most one presentation per room per slot
    for (room_id, t), pres_set in pres_for_room_slot.items():
        assert len(pres_set) <= 1

    # at most one room per presentation per slot (cfg default enforces this)
    for (pres_id, t), room_set in rooms_for_pres_slot.items():
        assert len(room_set) <= 1
