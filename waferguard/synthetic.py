"""Seeded synthetic images and a placement-derived oracle, with no OpenCV dependency."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Defect:
    id: str
    kind: str
    x: int
    y: int
    size: int  # Spot radius or scratch half-length, in pixels.
    contrast: int


def generate(seed: int, defects: tuple[Defect, ...] = (), noise: float = 2.0) -> np.ndarray:
    """Render a 256px unpatterned wafer with an illumination gradient and sensor noise."""
    y, x = np.ogrid[:256, :256]
    wafer = (x - 128) ** 2 + (y - 128) ** 2 <= 112**2
    surface = 116 + 0.10 * (x - 128) + 0.06 * (y - 128)
    image = np.where(wafer, surface, 12.0)
    for defect in defects:
        dx, dy = x - defect.x, y - defect.y
        if defect.kind == "spot":
            footprint = dx**2 + dy**2 <= defect.size**2
        elif defect.kind == "scratch":
            footprint = (np.abs(dx) <= defect.size) & (np.abs(dy) <= 1)
        else:
            raise ValueError(f"Unknown defect kind: {defect.kind}")
        image[footprint & wafer] += defect.contrast
    image += np.random.default_rng(seed).normal(0, noise, image.shape)
    return np.rint(image).clip(0, 255).astype(np.uint8)
