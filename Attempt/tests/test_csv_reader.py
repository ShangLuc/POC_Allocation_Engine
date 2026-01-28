import pytest

from app.infrastructure.csv_reader import read_students_csv


def test_read_students_csv_sniffs_semicolon_delimiter(tmp_path):
    # French Excel exports often use ';'
    p = tmp_path / "students.csv"
    p.write_text(
        "ID élève;Vague;Voeu 1;Voeu 2;Voeu 3;Voeu 4;Voeu 5\n"
        "S0;1;CONF_1;CONF_2;CONF_3;CONF_4;CONF_5\n",
        encoding="utf-8-sig",
    )

    presentation_ids, student_choices = read_students_csv(str(p))

    assert len(student_choices.choices) == 1
    assert len(presentation_ids) == 5


def test_read_students_csv_rejects_empty_file(tmp_path):
    p = tmp_path / "students.csv"
    p.write_text(
        "ID élève,Vague,Voeu 1,Voeu 2,Voeu 3,Voeu 4,Voeu 5\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(ValueError, match="No student rows detected"):
        read_students_csv(str(p))
