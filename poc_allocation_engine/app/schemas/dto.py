from __future__ import annotations

from typing import List, Dict
from pydantic import BaseModel


class SlotAssignment(BaseModel):
    slot: int
    presentation_id: str
    room_id: str


class StudentAllocation(BaseModel):
    student_index: int
    assignments: List[SlotAssignment]


class PresentationSession(BaseModel):
    presentation_id: str
    room_id: str
    slot: int
    student_indices: List[int]


class SolveResponse(BaseModel):
    status: str
    objective: float
    students: List[StudentAllocation]
    sessions: List[PresentationSession]
