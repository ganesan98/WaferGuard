"""Measure detection across defect sizes, contrasts, and noise levels."""

import csv
from pathlib import Path

from waferguard.inspection import RESIDUAL_THRESHOLD, inspect_image
from waferguard.matching import score
from waferguard.synthetic import Defect, generate


def main():
    output = Path("experiment_output")
    output.mkdir(exist_ok=True)

    radii = (1, 2, 3, 4)
    contrasts = (10, 25, 50, 75)
    noise_levels = (0, 2, 6)
    seeds = range(100, 110)

    rows = []

    for noise in noise_levels:
        clean_detections = 0

        for seed in seeds:
            clean_image = generate(seed, noise=noise)
            clean_detections += len(inspect_image(clean_image))

        for radius in radii:
            for contrast in contrasts:
                matches = 0
                missed = 0
                extras = 0

                for seed in seeds:
                    truth = (
                        Defect(
                            "probe",
                            "spot",
                            128,
                            128,
                            radius,
                            contrast,
                        ),
                    )

                    image = generate(seed, truth, noise=noise)
                    detections = inspect_image(image)
                    result = score(truth, detections, tolerance=3)

                    matches += len(result.matches)
                    missed += len(result.missed)
                    extras += len(result.false_positives)

                row = {
                    "threshold": RESIDUAL_THRESHOLD,
                    "radius_px": radius,
                    "contrast": contrast,
                    "noise_sigma": noise,
                    "frames": len(seeds),
                    "matched": matches,
                    "missed": missed,
                    "recall": matches / (matches + missed),
                    "extra_detections": extras,
                    "extras_per_frame": extras / len(seeds),
                    "clean_detections_per_frame": (
                        clean_detections / len(seeds)
                    ),
                }
                rows.append(row)

    path = output / "sensitivity.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} conditions to {path}")


if __name__ == "__main__":
    main()