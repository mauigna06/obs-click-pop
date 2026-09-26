"""Tier 1: drag-trail sampling and segment geometry."""

import pytest

from click_pop_core import trail_sample_reached, trail_segment_transform


def test_sample_requires_configured_distance():
    assert not trail_sample_reached(0, 0, 5.9, 0, 6)
    assert trail_sample_reached(0, 0, 6, 0, 6)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ((10, 20), (30, 20), (20, 20, 0, 28, 8)),
        ((10, 20), (10, 40), (10, 30, 90, 28, 8)),
        ((10, 20), (0, 10), (5, 15, -135, 10 * 2**0.5 + 8, 8)),
    ],
)
def test_segment_transform(start, end, expected):
    transform = trail_segment_transform(*start, *end, 8)

    assert transform == pytest.approx(expected)


def test_zero_length_segment_is_rejected():
    assert trail_segment_transform(10, 20, 10, 20, 8) is None