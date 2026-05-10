"""Tests for the sparkline rendering."""

from __future__ import annotations

from tama.history import DEFAULT_HISTORY_LEN, sparkline


def test_empty_input_returns_padded_spaces() -> None:
    result = sparkline([])
    assert result == " " * DEFAULT_HISTORY_LEN


def test_single_value_returns_one_block_right_aligned() -> None:
    result = sparkline([100], width=5)
    assert len(result) == 5
    assert result.rstrip() == "    █"  # 4 leading spaces then a full block


def test_progression_renders_increasing_blocks() -> None:
    """Ascending values should render as ascending block heights."""
    result = sparkline([0, 25, 50, 75, 100], width=5)
    assert len(result) == 5
    # The last character must be the tallest block.
    assert result[-1] == "█"
    # The first character is the shortest (▁), not a space.
    assert result[0] == "▁"


def test_none_renders_as_space() -> None:
    """A None slot in the middle of the history must come out as a space."""
    result = sparkline([50, None, 50], width=3)
    assert len(result) == 3
    assert result[1] == " "
    # The first and last cells should be the SAME block (both are value 50).
    assert result[0] == result[2]
    assert result[0] != " "


def test_clamps_out_of_range_values() -> None:
    result = sparkline([-100, 200], width=2)
    assert result[0] == "▁"
    assert result[1] == "█"


def test_truncates_to_width() -> None:
    result = sparkline([10, 20, 30, 40, 50, 60, 70], width=3)
    # Width 3 keeps only the LAST 3 values, right-aligned.
    assert len(result) == 3
    assert result[-1] == sparkline([70], width=1)[-1]
