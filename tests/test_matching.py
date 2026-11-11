import pytest

from waferguard.inspection import Detection
from waferguard.matching import score
from waferguard.synthetic import Defect


def spot(label, x):
    return Defect(label, "spot", x, 0, 2, 75)


def test_duplicate_is_false_positive_and_distant_truth_is_missed():
    result = score(
        (spot("seen", 10), spot("missed", 50)),
        (Detection(10, 0, 5), Detection(11, 0, 7)),
    )
    assert [match.truth_id for match in result.matches] == ["seen"]
    assert result.false_positives == (Detection(11, 0, 7),)
    assert [defect.id for defect in result.missed] == ["missed"]
    assert result.precision == result.recall == 0.5


def test_matching_can_reassign_to_avoid_an_artificial_miss():
    # First truth prefers x=1 but the second truth has no other viable candidate.
    result = score((spot("a", 0), spot("b", 4)), (Detection(1, 0, 5), Detection(-2, 0, 5)))
    assert [(match.truth_id, match.detection.x, match.error_px) for match in result.matches] == [
        ("a", -2, 2.0), ("b", 1, 3.0)
    ]
    assert result.precision == result.recall == 1


def test_just_outside_tolerance_is_both_a_false_positive_and_a_miss():
    result = score((spot("boundary", 0),), (Detection(3.01, 0, 5),))
    assert not result.matches
    assert len(result.false_positives) == len(result.missed) == 1


def test_empty_score_has_undefined_ratios():
    result = score((), ())
    assert result.precision is result.recall is None
    assert not result.matches and not result.false_positives and not result.missed


@pytest.mark.parametrize("tolerance", [-1, float("nan"), float("inf")])
def test_rejects_invalid_tolerance(tolerance):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        score((), (), tolerance)
