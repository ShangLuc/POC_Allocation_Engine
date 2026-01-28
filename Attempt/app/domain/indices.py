from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Indexer:
    """
    Flattens 3D decision variables into a single 1D vector x for scipy.optimize.milp.

    x = [ ae(e,p,t) for all e,p,t ]  concatenated with  [ as(p,s,t) for all p,s,t ]

    - ae: student -> presentation at time slot (binary)
    - as: presentation -> room at time slot (binary)
    """
    E: int  # number of students
    P: int  # number of presentations
    S: int  # number of rooms
    T: int  # number of global time slots (NOTE: doc implies 5 global slots, each wave attends 4)

    def ae_size(self) -> int:
        return self.E * self.P * self.T

    def as_size(self) -> int:
        return self.P * self.S * self.T

    def n_vars(self) -> int:
        return self.ae_size() + self.as_size()

    def ae_index(self, e: int, p: int, t: int) -> int:
        # ae is first block
        return (e * self.P * self.T) + (p * self.T) + t

    def as_index(self, p: int, s: int, t: int) -> int:
        # as is second block
        base = self.ae_size()
        return base + (p * self.S * self.T) + (s * self.T) + t
