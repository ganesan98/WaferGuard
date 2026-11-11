"""Write reproducible images, overlays, and a JSON qualification report."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import cv2
import numpy as np

from waferguard.inspection import inspect_file
from waferguard.matching import score
from waferguard.synthetic import Defect, generate


def write_png(path: Path, image: np.ndarray) -> None:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"Could not encode {path}")
    path.write_bytes(encoded.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("demo_output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    scenes = (
        ("mixed", 42, 6, (
            Defect("bright-particle", "spot", 85, 93, 4, 78),
            Defect("dark-scratch", "scratch", 160, 148, 11, -75),
            Defect("dark-particle", "spot", 130, 190, 3, -70),
        )),
        ("low-contrast", 8, 0, (Defect("faint", "spot", 128, 128, 4, 8),)),
    )
    report = {}
    for name, seed, noise, truth in scenes:
        image = generate(seed, truth, noise)
        source = args.output / f"{name}.png"
        write_png(source, image)
        detections = inspect_file(source)
        result = score(truth, detections)
        report[name] = {
            "seed": seed,
            "noise_sigma": noise,
            "tolerance_px": 3,
            "ground_truth": [asdict(defect) for defect in truth],
            **asdict(result),
            "precision": result.precision,
            "recall": result.recall,
        }

        overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        for defect in truth:
            cv2.circle(overlay, (defect.x, defect.y), 8, (255, 220, 0), 1)
        for hit in detections:
            cv2.drawMarker(overlay, (round(hit.x), round(hit.y)), (0, 255, 0), markerSize=7)
        write_png(args.output / f"{name}-overlay.png", overlay)

    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved two inspection cases and their score report to {args.output}")


if __name__ == "__main__":
    main()
