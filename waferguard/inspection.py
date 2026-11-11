"""Image-only system under test for the documented fixed inspection recipe."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


RESIDUAL_THRESHOLD = 24


class InspectionInputError(ValueError):
    """Input cannot be read or is outside the inspection recipe."""


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    area: int


def inspect_image(image: np.ndarray) -> tuple[Detection, ...]:
    """Return candidate centroids and areas for a 256x256 uint8 grayscale frame."""
    if not isinstance(image, np.ndarray) or image.shape != (256, 256) or image.dtype != np.uint8:
        raise InspectionInputError("Expected a 256x256 uint8 grayscale image")

    signal = image.astype(np.float32)
    background = cv2.GaussianBlur(signal, (0, 0), sigmaX=5)
    y, x = np.ogrid[:256, :256]
    usable = (x - 128) ** 2 + (y - 128) ** 2 <= 98**2
    foreground = usable & (np.abs(signal - background) >= RESIDUAL_THRESHOLD)
    count, _, stats, centers = cv2.connectedComponentsWithStats(
        foreground.astype(np.uint8), connectivity=8
    )
    detections = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= 5:
            x_center, y_center = centers[label]
            detections.append(Detection(float(x_center), float(y_center), area))
    return tuple(sorted(detections, key=lambda candidate: (candidate.y, candidate.x)))


def inspect_file(path: str | Path) -> tuple[Detection, ...]:
    """Decode a file without silently converting color images or bit depth."""
    try:
        encoded = Path(path).read_bytes()
        image = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_UNCHANGED) if encoded else None
    except (OSError, cv2.error) as exc:
        raise InspectionInputError(f"Could not read image: {path}") from exc
    if image is None:
        raise InspectionInputError(f"Could not decode image: {path}")
    return inspect_image(image)
