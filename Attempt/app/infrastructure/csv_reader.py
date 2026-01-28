from __future__ import annotations

import csv
from typing import List, Tuple

from app.domain.variables import (
    ProblemData,
    StudentChoices,
    build_presentation_id_map,
    canonicalize_label,
)


def _sniff_dialect(sample: str) -> csv.Dialect | None:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        return None


def read_students_csv(path: str) -> Tuple[List[str], StudentChoices]:
    students = []
    waves = []
    raw_choices = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = _sniff_dialect(sample)
        reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)
        for row in reader:
            waves.append(int(row["Vague"]))
            choices = [
                row["Voeu 1"],
                row["Voeu 2"],
                row["Voeu 3"],
                row["Voeu 4"],
                row["Voeu 5"],
            ]
            raw_choices.append(choices)
            students.append(row["ID élève"])

    if not students:
        raise ValueError(
            "No student rows detected in students CSV. "
            "Check delimiter (comma vs semicolon) and encoding."
        )

    all_labels = {
        label
        for choices in raw_choices
        for label in choices
        if label is not None and str(label).strip() != ""
    }
    if not all_labels:
        raise ValueError(
            "No presentation choices detected in students CSV (all choice cells empty)."
        )
    id_map = build_presentation_id_map(list(all_labels))

    choices_idx = [
        [id_map[canonicalize_label(lbl)] for lbl in choices]
        for choices in raw_choices
    ]

    return list(id_map.keys()), StudentChoices(choices=choices_idx, wave=waves)


def read_rooms_csv(path: str) -> Tuple[List[str], List[int]]:
    room_ids = []
    capacities = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = _sniff_dialect(sample)
        reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)
        for row in reader:
            room_ids.append(row["room_id"])
            capacities.append(int(row["capacity"]))

    return room_ids, capacities


def load_problem(
    students_csv: str,
    rooms_csv: str,
    T_global: int = 5,
) -> ProblemData:
    presentation_ids, student_choices = read_students_csv(students_csv)
    room_ids, capacities = read_rooms_csv(rooms_csv)

    return ProblemData(
        presentation_ids=presentation_ids,
        room_ids=room_ids,
        capacities=capacities,
        student_choices=student_choices,
        T_global=T_global,
    )
