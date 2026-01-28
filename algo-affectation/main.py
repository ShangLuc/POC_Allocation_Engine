# solver_forum_affectation.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional

import pandas as pd
from ortools.sat.python import cp_model


# ----------------------------
# Config: slot templates (5 slots per half-day)
# ----------------------------
MORNING_SLOTS = [("08:30", "09:00"),
                 ("09:15", "09:45"),
                 ("10:00", "10:30"),
                 ("10:45", "11:15"),
                 ("11:30", "12:00")]

AFTERNOON_SLOTS = [("13:30", "14:00"),
                   ("14:15", "14:45"),
                   ("15:00", "15:30"),
                   ("15:45", "16:15"),
                   ("16:30", "17:00")]

# Arrival times that determine whether student attends first 4 or last 4 slots
ARRIVAL_EARLY = {"08:30", "13:30"}
ARRIVAL_LATE = {"09:15", "14:15"}


# ----------------------------
# Helpers
# ----------------------------
def normalize_time_str(x: str) -> str:
    """
    Accepts: '8h30', '08:30', '8:30', '14:15', '14h15', '14:15:00'
    Returns: 'HH:MM'
    """
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()

    # Excel sometimes gives datetime/time objects; pandas can stringify oddly
    s = s.replace("h", ":")
    s = re.sub(r"\s+", "", s)
    # Keep only digits and :
    s = re.sub(r"[^0-9:]", "", s)

    parts = s.split(":")
    parts = [p for p in parts if p != ""]
    if len(parts) == 1 and len(parts[0]) in (3, 4):  # e.g. "830" or "1415"
        p = parts[0]
        hh = int(p[:-2])
        mm = int(p[-2:])
    elif len(parts) >= 2:
        hh = int(parts[0])
        mm = int(parts[1])
    else:
        raise ValueError(f"Cannot parse time: {x}")

    return f"{hh:02d}:{mm:02d}"


def normalize_date(x) -> str:
    """
    Returns YYYY-MM-DD
    """
    if pd.isna(x):
        return ""
    if isinstance(x, (datetime, )):
        return x.date().isoformat()
    s = str(x).strip()
    # common input: '26/03/2026'
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {x}")


def daypart_from_arrival(arrival_hhmm: str) -> str:
    hh = int(arrival_hhmm[:2])
    return "AM" if hh < 12 else "PM"


def allowed_slot_indices(arrival_hhmm: str) -> List[int]:
    """
    Early arrivals: slots 0-3 (4 slots)
    Late arrivals:  slots 1-4 (4 slots)
    """
    if arrival_hhmm in ARRIVAL_EARLY:
        return [0, 1, 2, 3]
    if arrival_hhmm in ARRIVAL_LATE:
        return [1, 2, 3, 4]
    raise ValueError(f"Arrival time {arrival_hhmm} not in expected set {ARRIVAL_EARLY | ARRIVAL_LATE}")


def slot_template(daypart: str) -> List[Tuple[str, str]]:
    return MORNING_SLOTS if daypart == "AM" else AFTERNOON_SLOTS


# ----------------------------
# Data models
# ----------------------------
@dataclass(frozen=True)
class Student:
    idx: int
    etablissement: str
    nom: str
    prenom: str
    id_national: str
    date: str          # YYYY-MM-DD
    arrival: str       # HH:MM
    daypart: str       # AM/PM
    wishes: Tuple[str, str, str, str, str]  # V1..V5


def load_rooms(capacity_xlsx_path: str) -> pd.DataFrame:
    """
    Expected columns (from your file): 'Salle N°', 'capacité' (plus others).
    """
    df = pd.read_excel(capacity_xlsx_path)
    # normalize col names
    df.columns = [str(c).strip() for c in df.columns]
    # try to find the room + capacity columns
    room_col = next((c for c in df.columns if c.lower().startswith("salle")), None)
    cap_col = next((c for c in df.columns if "cap" in c.lower()), None)
    if not room_col or not cap_col:
        raise ValueError(f"Could not find room/capacity columns in {df.columns.tolist()}")

    out = df[[room_col, cap_col]].copy()
    out.columns = ["room", "capacity"]
    out["room"] = out["room"].astype(str).str.strip()
    out["capacity"] = pd.to_numeric(out["capacity"], errors="coerce").fillna(0).astype(int)
    out = out[out["capacity"] > 0].drop_duplicates(subset=["room"]).reset_index(drop=True)
    if out.empty:
        raise ValueError("No valid rooms with capacity > 0 found.")
    return out


def load_students(students_csv_path: str) -> List[Student]:
    df = pd.read_csv(students_csv_path, encoding="latin1", sep="\t")



    #df = pd.read_csv(students_csv_path)

    # Expecting these columns based on your screenshot:
    # Etablissement, Nom de famille, Prenom, Date, Heure, ID National, Voeu 1..5
    # We'll be forgiving on casing/spaces.
    df.columns = [str(c).strip() for c in df.columns]

    def find_col(candidates: List[str]) -> str:
        for cand in candidates:
            for c in df.columns:
                if c.strip().lower() == cand.strip().lower():
                    return c
        raise ValueError(f"Missing column. Tried: {candidates}. Have: {df.columns.tolist()}")

    col_etab = find_col(["Etablissement"])
    col_nom = find_col(["Nom de famille", "Nom"])
    col_prenom = find_col(["Prenom", "Prénom"])
    col_date = find_col(["Date"])
    col_heure = find_col(["Heure"])
    col_id = find_col(["ID National", "Id National", "ID_National", "id"])

    vcols = []
    for i in range(1, 6):
        vcols.append(find_col([f"Voeu {i}", f"Vœu {i}", f"Voeu{i}", f"Vœu{i}"]))

    students: List[Student] = []
    for i, row in df.iterrows():
        date = normalize_date(row[col_date])
        arrival = normalize_time_str(row[col_heure])
        dp = daypart_from_arrival(arrival)
        wishes = tuple(str(row[c]).strip() for c in vcols)
        students.append(Student(
            idx=i,
            etablissement=str(row[col_etab]).strip(),
            nom=str(row[col_nom]).strip(),
            prenom=str(row[col_prenom]).strip(),
            id_national=str(row[col_id]).strip(),
            date=date,
            arrival=arrival,
            daypart=dp,
            wishes=wishes  # V1..V5
        ))
    return students


# ----------------------------
# Solver per half-day block
# ----------------------------

def solve_halfday(students, rooms_df, date, daypart,
                  overflow=0, time_limit_s=600, num_workers=8, random_seed=42):

    import gc
    from ortools.sat.python import cp_model

    # Filter students for this block
    block_students = [s for s in students if s.date == date and s.daypart == daypart]
    if not block_students:
        return pd.DataFrame(), pd.DataFrame()

    slots = slot_template(daypart)
    T = list(range(len(slots)))

    # Rooms and capacities with overflow
    cap = rooms_df.set_index("room")["capacity"].to_dict()
    cap = {str(r).strip(): int(c) + int(overflow) for r, c in cap.items()}
    rooms = list(cap.keys())

    # Activities in this block (filter empty + "nan")
    def ok_act(w):
        if w is None:
            return False
        s = str(w).strip()
        return s != "" and s.lower() != "nan"

    A = sorted({str(w).strip() for s in block_students for w in s.wishes if ok_act(w)})

    model = cp_model.CpModel()

    run = {}
    room_assign = {}

    for t in T:
        for a in A:
            run[(t, a)] = model.NewBoolVar(f"run_t{t}_a{a}")
            for r in rooms:
                room_assign[(t, a, r)] = model.NewBoolVar(f"room_t{t}_a{a}_r{r}")
            # No parallel same activity: exactly 1 room if runs, else 0
            model.Add(sum(room_assign[(t, a, r)] for r in rooms) == run[(t, a)])

    # One activity per room per slot
    for t in T:
        for r in rooms:
            model.Add(sum(room_assign[(t, a, r)] for a in A) <= 1)

    y = {}
    x = {}

    for s in block_students:
        v1, v2, v3, v4, v5 = [str(w).strip() for w in s.wishes]

        # Validate mandatory wishes exist
        if not ok_act(v1) or not ok_act(v2):
            raise ValueError(f"Student {s.idx} has empty mandatory wish: {s.wishes}")

        wish_set = [v1, v2, v3, v4, v5]
        wish_set = [w for w in wish_set if ok_act(w)]
        wish_set = list(dict.fromkeys(wish_set))  # dedup, stable

        # Create y vars
        for w in wish_set:
            y[(s.idx, w)] = model.NewBoolVar(f"y_s{s.idx}_a{w}")

        # Mandatory
        model.Add(y[(s.idx, v1)] == 1)
        model.Add(y[(s.idx, v2)] == 1)

        # Optional: exactly 2 among v3,v4,v5 (distinct non-empty)
        optional = [w for w in [v3, v4, v5] if ok_act(w)]
        optional = list(dict.fromkeys(optional))
        if len(optional) < 2:
            raise ValueError(f"Student {s.idx} has <2 distinct optional wishes: {s.wishes}")
        model.Add(sum(y[(s.idx, w)] for w in optional) == 2)

        allowed_ts = allowed_slot_indices(s.arrival)

        # Assign exactly 1 activity per allowed slot
        for t in allowed_ts:
            for w in wish_set:
                x[(s.idx, t, w)] = model.NewBoolVar(f"x_s{s.idx}_t{t}_a{w}")
                model.Add(x[(s.idx, t, w)] <= run[(t, w)])
            model.Add(sum(x[(s.idx, t, w)] for w in wish_set) == 1)

        # Each selected activity scheduled exactly once across 4 slots
        for w in wish_set:
            model.Add(sum(x[(s.idx, t, w)] for t in allowed_ts) == y[(s.idx, w)])

    # Capacity constraints
    for t in T:
        for a in A:
            assigned = []
            for s in block_students:
                allowed_ts = allowed_slot_indices(s.arrival)
                if t in allowed_ts and (s.idx, t, a) in x:
                    assigned.append(x[(s.idx, t, a)])

            if assigned:
                model.Add(
                    sum(assigned) <= sum(cap[r] * room_assign[(t, a, r)] for r in rooms)
                )
            else:
                model.Add(run[(t, a)] == 0)

    # Small objective to help search
    model.Minimize(sum(run[(t, a)] for t in T for a in A))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = int(num_workers)
    solver.parameters.random_seed = int(random_seed)

    status = solver.Solve(model)

    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # hard free
        del model, solver
        gc.collect()
        raise RuntimeError(f"{date} {daypart} status={status_name} (overflow={overflow})")

    # Build room plan
    rooms_rows = []
    for t in T:
        slot_start, slot_end = slots[t]
        for a in A:
            if solver.Value(run[(t, a)]) == 1:
                chosen_room = None
                for r in rooms:
                    if solver.Value(room_assign[(t, a, r)]) == 1:
                        chosen_room = r
                        break
                if not chosen_room:
                    continue

                cnt = 0
                for s in block_students:
                    if (s.idx, t, a) in x:
                        cnt += solver.Value(x[(s.idx, t, a)])

                rooms_rows.append({
                    "date": date,
                    "demi_journee": daypart,
                    "slot_start": slot_start,
                    "slot_end": slot_end,
                    "salle": chosen_room,
                    "capacite": cap[chosen_room],
                    "activite": a,
                    "nb_inscrits": cnt,
                    "overflow_used": overflow,
                })

    planning_rooms_df = pd.DataFrame(rooms_rows)

    # Build student plan
    student_rows = []
    for s in block_students:
        allowed_ts = allowed_slot_indices(s.arrival)
        slot_assignments = []

        for t in allowed_ts:
            chosen_a = None
            for w in [str(v).strip() for v in s.wishes]:
                if ok_act(w) and (s.idx, t, w) in x and solver.Value(x[(s.idx, t, w)]) == 1:
                    chosen_a = w
                    break
            if chosen_a is None:
                raise RuntimeError(f"Missing assignment for student {s.idx} slot {t}")

            chosen_room = None
            for r in rooms:
                if solver.Value(room_assign[(t, chosen_a, r)]) == 1:
                    chosen_room = r
                    break
            if chosen_room is None:
                raise RuntimeError(f"Missing room for {chosen_a} at slot {t}")

            st, en = slots[t]
            slot_assignments.append((st, en, chosen_a, chosen_room))

        row = {
            "etablissement": s.etablissement,
            "nom": s.nom,
            "prenom": s.prenom,
            "id_national": s.id_national,
            "date": s.date,
            "demi_journee": s.daypart,
            "heure_arrivee": s.arrival,
            "voeu1": s.wishes[0],
            "voeu2": s.wishes[1],
            "voeu3": s.wishes[2],
            "voeu4": s.wishes[3],
            "voeu5": s.wishes[4],
            "voeux_retenus": ", ".join([a for _, _, a, _ in slot_assignments]),
            "overflow_used": overflow,
        }

        for i, (st, en, act, room) in enumerate(slot_assignments, start=1):
            row[f"slot_{i}_start"] = st
            row[f"slot_{i}_end"] = en
            row[f"slot_{i}_activite"] = act
            row[f"slot_{i}_salle"] = room

        student_rows.append(row)

    planning_students_df = pd.DataFrame(student_rows)

    # hard free
    del model, solver
    gc.collect()

    return planning_students_df, planning_rooms_df


def solve_all(students_csv_path, capacities_xlsx_path,
              out_students_csv="planning_students.csv",
              out_rooms_csv="planning_salles.csv"):

    import gc

    rooms_df = load_rooms(capacities_xlsx_path)
    students = load_students(students_csv_path)

    blocks = sorted({(s.date, s.daypart) for s in students})
    if not blocks:
        raise RuntimeError("No (date, demi-journée) blocks found.")

    all_students_out = []
    all_rooms_out = []

    print(f"Found {len(blocks)} half-day blocks: {blocks}")

    for i, (date, daypart) in enumerate(blocks, 1):
        print(f"\n=== Solving block {i}/{len(blocks)} : {date} {daypart} ===")

        solved = False
        last_error = None

        # Strategy:
        # - first try overflow 0..3 with normal time
        # - if UNKNOWN appears, retry same overflow with longer time before increasing overflow
        base_time = 600
        long_time = 1800  # 30 min for stubborn blocks

        for overflow in range(0, 4):
            for attempt, tlim in enumerate([base_time, long_time], start=1):
                print(f"→ overflow +{overflow}, attempt {attempt}/2, time_limit={tlim}s")

                try:
                    ps, pr = solve_halfday(
                        students, rooms_df, date, daypart,
                        overflow=overflow,
                        time_limit_s=tlim,
                        num_workers=8,
                        random_seed=42
                    )

                    print(f"✔ Solved {date} {daypart} with overflow +{overflow} (time_limit={tlim}s)")
                    all_students_out.append(ps)
                    all_rooms_out.append(pr)
                    solved = True
                    break

                except RuntimeError as e:
                    last_error = str(e)
                    print(f"✖ Failed: {last_error}")

                    # If it was INFEASIBLE, no point retrying longer for same overflow
                    if "INFEASIBLE" in last_error:
                        break

                    # Free memory between attempts
                    gc.collect()

            if solved:
                break

        if not solved:
            raise RuntimeError(f"Block {date} {daypart} failed after overflow 0..3. Last error: {last_error}")

        # Free memory before next block
        gc.collect()

    out_students = pd.concat(all_students_out, ignore_index=True)
    out_rooms = pd.concat(all_rooms_out, ignore_index=True)

    out_students.to_csv(out_students_csv, index=False, encoding="utf-8-sig")
    out_rooms.to_csv(out_rooms_csv, index=False, encoding="utf-8-sig")

    print("\n=== ALL BLOCKS SOLVED ===")
    print(f"Wrote: {out_students_csv} ({len(out_students)} rows)")
    print(f"Wrote: {out_rooms_csv} ({len(out_rooms)} rows)")




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Forum student affectation solver (CP-SAT)")
    parser.add_argument("--students_csv", required=True, help="Path to students CSV")
    parser.add_argument("--capacities_xlsx", required=True, help="Path to room capacities XLSX")
    parser.add_argument("--out_students_csv", default="planning_students.csv")
    parser.add_argument("--out_rooms_csv", default="planning_salles.csv")
    args = parser.parse_args()

    solve_all(args.students_csv, args.capacities_xlsx, args.out_students_csv, args.out_rooms_csv)
