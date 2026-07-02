
# POC Allocation Engine

Solve a student-to-presentation allocation problem with room/time constraints.

This project exposes a small FastAPI service with a single endpoint (`POST /solve`) that:
- reads two CSV files (students choices + rooms) that u must generate via exampeles/geenrate_dummy_data.py
- builds and solves an optimization model (OR-Tools CP-SAT)
- returns a JSON solution
- writes a flat CSV export to `examples/result.csv`

## Requirements

- Windows (commands below assume PowerShell)
- Python 3.11+

## Optional local config

If you want a placeholder for local settings, copy [.env.example](../.env.example) to `.env`.
The current app does not require secrets; this file is mainly a template for local launch values.

## Install

Create a virtual environment (recommended):

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the API

Start the server with auto-reload:

```powershell
.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

The API listens on:

```
http://127.0.0.1:8000
```

## Call the solver

Send the input CSV files as multipart form-data:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/solve?time_limit=20" \
	-F "students_csv=@examples/students_choices.csv" \
	-F "rooms_csv=@examples/rooms.csv"
```

Notes:
- Run the command from the repo root (`C:\Users\...\poc_allocation_engine`) so relative paths like `examples/...` work.
- The HTTP response is JSON. A CSV export is written to disk (see next section).

## Outputs

### JSON response

The endpoint returns:
- `status`: `OPTIMAL`/`FEASIBLE`
- `objective`: objective value (float)
- `students`: per-student assignments
- `sessions`: per (presentation, slot) session with list of students
- `exported_csv`: filesystem path of the CSV that was written

### CSV export

On every successful solve, the server writes:

```
examples/result.csv
```

CSV schema:

```
student_index,slot,presentation_id,room_id
```

One row per assigned (student, slot).

## Input CSV formats

### Students choices CSV

Headers (French):

```
ID élève,Vague,Voeu 1,Voeu 2,Voeu 3,Voeu 4,Voeu 5
```

- `Vague` must be `1` or `2`
- each student must have exactly 5 choices

### Rooms CSV

Headers:

```
room_id,capacity
```

## Generate dummy data

This overwrites `examples/students_choices.csv` and `examples/rooms.csv`:

```powershell
.venv\Scripts\python.exe examples\generate_dummy_data.py
```

## Run tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Solver backend

The current backend is **OR-Tools CP-SAT**.

Implementation locations:
- model builder: `app/domain/model.py`
- constraints: `app/domain/constraints.py`
- solver wrapper: `app/infrastructure/solver.py`

## Troubleshooting

### `uvicorn` is not recognized

Use the venv Python module form:

```powershell
.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

### `curl: (26) Failed to open/read local data`

You are not in the repo root. Run:

```powershell
Set-Location C:\Users\walid\dev\poc_allocation_engine
```

Then retry the `curl.exe` command.
