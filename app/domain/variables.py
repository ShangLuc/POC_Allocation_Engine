from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Sequence


def canonicalize_label(label: str) -> str:
    """
    Deterministically generate a stable ID from a human label:
      - strip accents
      - lowercase
      - keep alnum + underscore
      - collapse underscores

    Example:
      "Conférence - IA & Santé" -> "conference_ia_sante"
    """
    if label is None:
        raise ValueError("label is None")
    x = unicodedata.normalize("NFKD", label)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = x.lower().strip()
    x = re.sub(r"[^a-z0-9]+", "_", x)
    x = re.sub(r"_+", "_", x).strip("_")
    if not x:
        raise ValueError(f"empty canonical id from label={label!r}")
    return x


@dataclass(frozen=True)
class StudentChoices:
    """
    choices[e] = list of 5 presentation indices (0..P-1), in order of preference.
    wave[e] in {1,2}
    """
    choices: List[List[int]]
    wave: List[int]


@dataclass(frozen=True)
class ProblemData:
    """
    Domain-level, solver-ready data.

    Requirements:
    - P presentations mapped to indices [0..P-1]
    - S rooms mapped to indices [0..S-1]
    - capacities[s] >= 0
    - student_choices.choices[e] length == 5, all values in [0..P-1]
    - wave values are 1 or 2
    """
    presentation_ids: List[str]               # length P
    room_ids: List[str]                       # length S
    capacities: List[int]                     # length S
    student_choices: StudentChoices
    T_global: int = 5                         # doc constraints imply 5 global slots


def build_presentation_id_map(labels: Sequence[str]) -> Dict[str, int]:
    """
    Deterministic label->index mapping (stable across runs given same label list).
    - canonicalize
    - sort by canonical id to avoid input-order ambiguity
    """
    canon = [(canonicalize_label(lbl), lbl) for lbl in labels]
    canon.sort(key=lambda x: x[0])
    mapping: Dict[str, int] = {}
    for idx, (cid, original) in enumerate(canon):
        if cid in mapping:
            raise ValueError(f"Duplicate canonical id {cid!r} from labels; labels not unique.")
        mapping[cid] = idx
    return mapping
