"""One-to-one location matching and diagnostics for small qualification scenes."""

from dataclasses import dataclass
from math import dist, isfinite

from waferguard.inspection import Detection
from waferguard.synthetic import Defect


@dataclass(frozen=True)
class Match:
    truth_id: str
    detection: Detection
    error_px: float


@dataclass(frozen=True)
class Score:
    matches: tuple[Match, ...]
    false_positives: tuple[Detection, ...]
    missed: tuple[Defect, ...]

    @property
    def precision(self) -> float | None:
        total = len(self.matches) + len(self.false_positives)
        return len(self.matches) / total if total else None

    @property
    def recall(self) -> float | None:
        total = len(self.matches) + len(self.missed)
        return len(self.matches) / total if total else None


def score(
    truth: tuple[Defect, ...],
    detections: tuple[Detection, ...],
    tolerance: float = 3.0,
) -> Score:
    """Maximize valid pairs using augmenting paths, with nearest candidates tried first."""
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be finite and nonnegative")

    errors = [
        [dist((defect.x, defect.y), (hit.x, hit.y)) for hit in detections]
        for defect in truth
    ]
    candidates = [
        sorted(
            (index for index, error in enumerate(row) if error <= tolerance),
            key=row.__getitem__,
        )
        for row in errors
    ]
    owners: dict[int, int] = {}

    def assign(truth_index: int, visited: set[int]) -> bool:
        for index in candidates[truth_index]:
            if index in visited:
                continue
            visited.add(index)
            if index not in owners or assign(owners[index], visited):
                owners[index] = truth_index
                return True
        return False

    for truth_index in range(len(truth)):
        assign(truth_index, set())

    matched_truth = set(owners.values())
    return Score(
        matches=tuple(
            Match(truth[t].id, detections[d], errors[t][d])
            for d, t in sorted(owners.items(), key=lambda pair: pair[1])
        ),
        false_positives=tuple(hit for d, hit in enumerate(detections) if d not in owners),
        missed=tuple(defect for t, defect in enumerate(truth) if t not in matched_truth),
    )
