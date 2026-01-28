import pandas as pd

STUDENTS_FILE = "students.csv"
PLANNING_STUDENTS_FILE = "planning_students.csv"
PLANNING_ROOMS_FILE = "planning_salles.csv"
ROOMS_FILE = "Capacités salles TSE.xlsx"


def load_rooms():
    df = pd.read_excel(ROOMS_FILE)
    df.columns = [c.strip() for c in df.columns]

    room_col = next(c for c in df.columns if c.lower().startswith("salle"))
    cap_col = next(c for c in df.columns if "cap" in c.lower())

    df = df[[room_col, cap_col]]
    df.columns = ["room", "capacity"]

    df["room"] = df["room"].astype(str).str.strip()
    df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce")
    df = df.dropna(subset=["room", "capacity"])

    return df.set_index("room")["capacity"].to_dict()


def log(msg):
    print(msg)


def test_student_has_4_activities(df_students):
    log("\n[TEST] Each student has exactly 4 activities")
    errors = 0
    slot_cols = [c for c in df_students.columns if "_activite" in c]

    for i, row in df_students.iterrows():
        acts = [row[c] for c in slot_cols if pd.notna(row[c])]
        if len(acts) != 4:
            log(f" Student {row['id_national']} has {len(acts)} activities: {acts}")
            errors += 1

    log(f"Result: {errors} errors\n")


def test_voeu1_voeu2(df_students):
    log("[TEST] Voeu1 and Voeu2 are respected")
    errors = 0
    for _, row in df_students.iterrows():
        chosen = row["voeux_retenus"]
        if row["voeu1"] not in chosen or row["voeu2"] not in chosen:
            log(f" Student {row['id_national']} missing V1 or V2: {chosen}")
            errors += 1
    log(f"Result: {errors} errors\n")


def test_two_of_last_three(df_students):
    log("[TEST] Exactly 2 of voeu3-voeu5 selected")
    errors = 0
    for _, row in df_students.iterrows():
        chosen = set(row["voeux_retenus"].split(", "))
        opt = {row["voeu3"], row["voeu4"], row["voeu5"]}
        opt = {v for v in opt if pd.notna(v)}

        if len(chosen & opt) != 2:
            log(f" Student {row['id_national']} optional mismatch: {chosen & opt}")
            errors += 1
    log(f"Result: {errors} errors\n")


def test_room_capacity(df_rooms, room_caps):
    log("[TEST] Room capacities respected")
    errors = 0
    for _, row in df_rooms.iterrows():
        room = str(row["salle"]).strip()
        nb = int(row["nb_inscrits"])
        cap = room_caps.get(room)

        if cap is None:
            log(f"Unknown room {room}")
            continue

        if nb > cap:
            log(f" {row['date']} {row['slot_start']} {room}: {nb}/{cap}")
            errors += 1
    log(f"Result: {errors} errors\n")


def test_one_activity_per_room_per_slot(df_rooms):
    log("[TEST] One activity per room per slot")
    errors = 0
    grouped = df_rooms.groupby(["date", "demi_journee", "slot_start", "salle"])

    for key, group in grouped:
        if len(group) > 1:
            log(f" Room double-booked: {key}")
            errors += 1
    log(f"Result: {errors} errors\n")


def test_no_parallel_activity(df_rooms):
    log("[TEST] No parallel same activity")
    errors = 0
    grouped = df_rooms.groupby(["date", "demi_journee", "slot_start", "activite"])

    for key, group in grouped:
        if len(group) > 1:
            log(f" Parallel activity: {key}")
            errors += 1
    log(f"Result: {errors} errors\n")


def test_students_slots(df_students):
    log("[TEST] Students are scheduled only in valid slots")
    errors = 0

    for _, row in df_students.iterrows():
        arrival = row["heure_arrivee"]

        if arrival in ("08:30", "13:30"):
            if row["slot_4_end"] in ("12:00", "17:00"):
                log(f" Early student ends too late: {row['id_national']}")
                errors += 1

        if arrival in ("09:15", "14:15"):
            if row["slot_1_start"] in ("08:30", "13:30"):
                log(f" Late student starts too early: {row['id_national']}")
                errors += 1

    log(f"Result: {errors} errors\n")


def main():
    log("Loading files...")
    df_students = pd.read_csv(PLANNING_STUDENTS_FILE)
    df_rooms = pd.read_csv(PLANNING_ROOMS_FILE)
    room_caps = load_rooms()

    log("\n===== RUNNING CONSTRAINT TESTS =====")

    test_student_has_4_activities(df_students)
    test_voeu1_voeu2(df_students)
    test_two_of_last_three(df_students)
    test_one_activity_per_room_per_slot(df_rooms)
    test_no_parallel_activity(df_rooms)
    test_students_slots(df_students)
    test_room_capacity(df_rooms, room_caps)

    log("===== TESTS COMPLETED =====")


if __name__ == "__main__":
    main()
