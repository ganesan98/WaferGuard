"""Investigate how spacing affects two-defect detection."""

import csv
import json
from pathlib import Path

import cv2

from waferguard.inspection import inspect_image
from waferguard.matching import score
from waferguard.synthetic import Defect, generate


def main():
    output = Path("experiment_output") / "separation"
    output.mkdir(parents=True, exist_ok=True)

    rows = []

    for separation in range(2, 21, 2):
        left_x = 128 - separation // 2
        right_x = 128 + separation // 2

        truth = (
            Defect("left", "spot", left_x, 128, 3, 75),
            Defect("right", "spot", right_x, 128, 3, 75),
        )

        image = generate(seed=42, defects=truth, noise=0)
        detections = inspect_image(image)
        result = score(truth, detections, tolerance=3)

        overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        for defect in truth:
            cv2.circle(
                overlay,
                (defect.x, defect.y),
                5,
                (255, 220, 0),
                1,
            )

        for detection in detections:
            cv2.drawMarker(
                overlay,
                (round(detection.x), round(detection.y)),
                (0, 255, 0),
                markerSize=7,
            )

        path = output / f"spacing-{separation:02d}px.png"
        ok, encoded = cv2.imencode(".png", overlay)

        if not ok:
            raise RuntimeError(f"Could not encode {path}")

        path.write_bytes(encoded.tobytes())

        rows.append({
            "separation_px": separation,
            "seed": 42,
            "radius_px": 3,
            "contrast": 75,
            "noise_sigma": 0,
            "physical_footprints_overlap": separation <= 6,
            "candidates": len(detections),
            "matched": len(result.matches),
            "missed": len(result.missed),
            "extra_detections": len(result.false_positives),
            "candidate_centers": json.dumps([
                [detection.x, detection.y]
                for detection in detections
            ]),
        })

    report = output / "separation.csv"

    with report.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved spacing measurements and overlays to {output}")


if __name__ == "__main__":
    main()