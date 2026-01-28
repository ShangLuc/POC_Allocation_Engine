import csv
import random
import string


def rand_label(prefix, i):
    return f"{prefix}_{i}"


def generate_students_csv(
    path: str,
    n_students: int,
    presentations: list[str],
):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID élève", "Vague",
            "Voeu 1", "Voeu 2", "Voeu 3", "Voeu 4", "Voeu 5"
        ])

        for i in range(n_students):
            choices = random.sample(presentations, 5)
            wave = random.choice([1, 2])
            writer.writerow([f"S{i}", wave, *choices])


def generate_rooms_csv(path: str, n_rooms: int, capacity: int):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["room_id", "capacity"])
        rooms = [
            ("A012", 32),
            ("A013", 42),
            ("A016", 32),
            ("A017", 36),
            ("A101", 26),
            ("A115", 38),
            ("A116", 40),
            ("J007", 16),
            ("J008", 16),
            ("J009", 16),
            ("J012", 20),
            ("J020", 112),
            ("J021", 212),
            ("J022", 212),
            ("J106", 30),
            ("J107", 16),
            ("J108", 32),
            ("J109", 32),
            ("J110", 36),
            ("J204", 30),
            ("I013", 50),
            ("D03", 80),
        ]
        writer.writerows(rooms)


if __name__ == "__main__":
    presentations = [rand_label("CONF", i) for i in range(30)]

    generate_students_csv(
        "examples/students_choices.csv",
        n_students=1000,
        presentations=presentations,
    )

    generate_rooms_csv(
        "examples/rooms.csv",
        n_rooms=0,
        capacity=0,
    )

    print("Dummy data generated.")
