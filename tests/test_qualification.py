from dataclasses import asdict

import cv2
import numpy as np
import pytest

from waferguard import inspection
from waferguard.inspection import InspectionInputError, inspect_file, inspect_image
from waferguard.matching import score
from waferguard.synthetic import Defect, generate


MIXED = (
    Defect("bright-particle", "spot", 85, 93, 4, 78),
    Defect("dark-scratch", "scratch", 160, 148, 11, -75),
    Defect("dark-particle", "spot", 130, 190, 3, -70),
)


def require_all_detected(seed, truth, detections):
    result = score(truth, detections, tolerance=3)
    assert not result.missed and not result.false_positives, (
        f"seed={seed}; missed={[asdict(defect) for defect in result.missed]}; "
        f"extra={result.false_positives}; matched={result.matches}"
    )


@pytest.mark.parametrize("seed,noise", [(19, 0), (41, 2), (211, 6)])
def test_q01_clean_wafer_has_zero_false_positives(seed, noise):
    require_all_detected(seed, (), inspect_image(generate(seed, noise=noise)))


def test_q02_single_particle_on_decoded_wafer(tmp_path):
    truth = MIXED[:1]
    ok, encoded = cv2.imencode(".png", generate(11, truth))
    assert ok
    path = tmp_path / "wafer.png"
    path.write_bytes(encoded.tobytes())
    require_all_detected(11, truth, inspect_file(path))


def test_q03_mixed_defects_across_seeded_noise_batch():
    for seed in range(200, 232):
        truth = (
            Defect("bright-particle", "spot", 80 + seed % 13, 85 + seed % 7, 4, 78),
            Defect("dark-scratch", "scratch", 150 + seed % 9, 143 + seed % 11, 11, -75),
            Defect("dark-particle", "spot", 126 + seed % 11, 180 + seed % 17, 3, -70),
        )
        require_all_detected(seed, truth, inspect_image(generate(seed, truth, noise=6)))


@pytest.mark.parametrize("radius,expected_hits", [(1, 1), (2, 1), (3, 1), (4, 1)])
def test_q04_spot_size_sweep(radius, expected_hits):
    # Fixed high contrast, zero noise, and a single position define this sweep.
    truth = (Defect("probe", "spot", 128, 128, radius, 75),)
    result = score(truth, inspect_image(generate(7, truth, noise=0)))
    assert len(result.matches) == expected_hits
    assert not result.false_positives


def test_q04_single_pixel_response_is_filtered():
    truth = (Defect("one-pixel", "spot", 128, 128, 0, 75),)
    result = score(truth, inspect_image(generate(7, truth, noise=0)))
    assert result.missed == truth
    assert not result.false_positives


def test_q05_excluded_edge_does_not_raise_false_positive():
    edge = Defect("edge-particle", "spot", 233, 128, 2, 95)
    assert inspect_image(generate(8, (edge,))) == ()


def test_q06_repeatability():
    image = generate(42, MIXED, noise=6)
    snapshot = image.copy()
    assert np.array_equal(snapshot, generate(42, MIXED, noise=6))
    assert not np.array_equal(snapshot, generate(43, MIXED, noise=6))
    first = inspect_image(image)
    require_all_detected(42, MIXED, first)
    assert all(inspect_image(image) == first for _ in range(5))
    assert np.array_equal(snapshot, image)


@pytest.mark.parametrize("data", [b"", b"not a PNG", None], ids=["empty", "corrupt", "missing"])
def test_q07_invalid_files_raise_controlled_error(tmp_path, data):
    path = tmp_path / "broken.png"
    if data is not None:
        path.write_bytes(data)
    with pytest.raises(InspectionInputError, match="Could not (read|decode) image"):
        inspect_file(path)


@pytest.mark.parametrize(
    "shape,dtype", [((128, 256), np.uint8), ((256, 256, 3), np.uint8), ((256, 256), np.uint16)],
    ids=["wrong-size", "color", "16-bit"],
)
def test_q07_rejects_unsupported_encoded_frames(tmp_path, shape, dtype):
    ok, encoded = cv2.imencode(".png", np.zeros(shape, dtype=dtype))
    assert ok
    path = tmp_path / "unsupported.png"
    path.write_bytes(encoded.tobytes())
    with pytest.raises(InspectionInputError, match="256x256 uint8 grayscale"):
        inspect_file(path)


def test_q08_low_contrast_miss_is_reported():
    truth = (Defect("faint", "spot", 128, 128, 4, 8),)
    result = score(truth, inspect_image(generate(8, truth, noise=0)))
    assert result.missed == truth
    assert result.recall == 0
    assert result.precision is None


def test_q09_qualification_rejects_threshold_regression(monkeypatch):
    monkeypatch.setattr(inspection, "RESIDUAL_THRESHOLD", 100)
    with pytest.raises(AssertionError, match=r"seed=11; missed=.*bright-particle"):
        require_all_detected(11, MIXED[:1], inspect_image(generate(11, MIXED[:1])))
