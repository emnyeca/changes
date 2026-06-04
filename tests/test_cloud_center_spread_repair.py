"""Tests for fit_cloud_center_spread_voice_vector and related center/spread repair."""

from __future__ import annotations

import dataclasses

from changes.voice_leading import (
    fit_cloud_center_spread_voice_vector,
    generate_voice_leading,
)
from changes.voicing import progression_to_voicings


def _repair(notes, *, center=60, smin=14, smax=16, tol=2, seed=None, ci=1):
    return fit_cloud_center_spread_voice_vector(
        notes, notes,
        center_midi=center, spread_min=smin, spread_max=smax,
        average_tolerance=tol, tie_break_seed=seed, chord_index=ci,
    )


# ── Closed voicing repair ─────────────────────────────────────────────────────
# Use notes tightly clustered around center so the octave slide stays within spread_max.
# [57,58,59,61,62,63]: avg=60 (no avg repair needed), spread=6 < 14.
# mid_lo=59, mid_hi=61; either option gives new_spread=16 which is within [14,16].

def test_closed_voicing_repair_expands_spread_when_feasible():
    notes_in = [57, 58, 59, 61, 62, 63]  # spread=6, avg=60, repair fits in [14,16]
    result = _repair(notes_in)
    new_spread = max(result) - min(result)
    assert new_spread > 6, "Closed repair must increase spread"
    assert new_spread <= 16, "Closed repair must not overshoot spread_max"


def test_closed_voicing_repair_meets_spread_min():
    notes_in = [57, 58, 59, 61, 62, 63]
    result = _repair(notes_in)
    assert max(result) - min(result) >= 14, "Spread must reach spread_min after repair"


# ── Average too low repair ─────────────────────────────────────────────────────

def test_average_too_low_repair_raises_average():
    notes_in = [48, 52, 55, 57, 59, 62]  # avg=55.5, center=60, tol=2 → too low
    result = _repair(notes_in)
    old_avg = sum(notes_in) / len(notes_in)
    new_avg = sum(result) / len(result)
    assert new_avg > old_avg, "Average must increase after too-low repair"
    assert abs(new_avg - 60) <= abs(old_avg - 60), "Average must move closer to center"


def test_average_too_low_lowest_note_moved_up():
    notes_in = [48, 52, 55, 57, 59, 62]
    result = _repair(notes_in)
    # lowest note 48 should no longer be present (was slid up by 12)
    assert 48 not in result, "Original lowest note should be replaced"
    assert min(result) > 48, "New lowest note should be higher"


# ── Average too high repair ────────────────────────────────────────────────────

def test_average_too_high_repair_lowers_average():
    notes_in = [58, 62, 65, 67, 70, 75]  # avg > 63 (center+2+something)
    result = _repair(notes_in)
    old_avg = sum(notes_in) / len(notes_in)
    new_avg = sum(result) / len(result)
    assert new_avg < old_avg, "Average must decrease after too-high repair"
    assert abs(new_avg - 60) <= abs(old_avg - 60), "Average must move closer to center"


# ── Spread too wide repair ─────────────────────────────────────────────────────

def test_spread_too_wide_repair_reduces_spread():
    # spread=26 > spread_max=16; low=46 farther from center; slide 46→58 gives spread=15 (in range)
    notes_in = [46, 57, 59, 60, 62, 72]
    result = _repair(notes_in)
    old_spread = max(notes_in) - min(notes_in)
    new_spread = max(result) - min(result)
    assert new_spread < old_spread, "Open repair must decrease spread"
    assert new_spread <= 16, "Spread must not exceed spread_max after repair"


# ── Stability: same chord repeated stays stable ───────────────────────────────

def test_repeated_chord_produces_stable_voicing():
    # After the first few chords, consecutive same chords must produce identical notes.
    voicings = progression_to_voicings([["Cmaj7"] * 6])
    led = generate_voice_leading(
        voicings, center_midi=60, spread_min=14, spread_max=16, average_tolerance=2,
        tie_break_seed=None,
    )
    # From chord 3 onwards, must be identical (convergence within 2 passes)
    assert led[2] == led[3] == led[4] == led[5], "Repair must converge to stable voicing"


def test_stability_implies_hold_behavior_for_same_chord():
    # The stable voicing's first voice note must be repeated → hold merges events.
    voicings = progression_to_voicings([["C7", "C7", "C7"]])
    led = generate_voice_leading(
        voicings, center_midi=60, spread_min=14, spread_max=16, average_tolerance=2,
        tie_break_seed=None,
    )
    # Chords 2 and 3 (indices 1 and 2) should produce identical voicings.
    assert led[1] == led[2], "Consecutive same chords must produce identical voicings after stabilization"


# ── Repair output constraints ─────────────────────────────────────────────────

def test_repair_preserves_pitch_class_set():
    notes_in = [55, 57, 59, 60, 62, 64]  # avg OK, spread might need repair
    result = _repair(notes_in)
    in_pcs = sorted(n % 12 for n in notes_in)
    out_pcs = sorted(n % 12 for n in result)
    assert in_pcs == out_pcs, "Repair must preserve pitch class multiset"


def test_repair_preserves_voice_count():
    notes_in = [55, 57, 59, 60, 62, 64]
    result = _repair(notes_in)
    assert len(result) == 6


# ── Seed tiebreak determinism ──────────────────────────────────────────────────

def test_repair_deterministic_with_same_seed():
    notes_in = [58, 59, 61, 63, 66, 68]  # closed voicing → tiebreak fires
    r1 = _repair(notes_in, seed=42, ci=2)
    r2 = _repair(notes_in, seed=42, ci=2)
    assert r1 == r2


def test_repair_may_differ_with_different_seeds():
    # [57,58,59,61,62,63]: equidistant mid pair (59,61), repair stays in range → tiebreak fires.
    # Different seeds → different directions → different outcomes.
    notes_in = [57, 58, 59, 61, 62, 63]
    results = {tuple(sorted(_repair(notes_in, seed=s, ci=1))) for s in range(20)}
    assert len(results) >= 2, "Different seeds should produce different outcomes (when tiebreak fires)"


# ── generate_voice_leading center mode validation ─────────────────────────────

def test_generate_voice_leading_center_mode_rejects_mixed_params():
    import pytest
    voicings = [[60, 62, 64, 65, 67, 69]]
    with pytest.raises(ValueError):
        generate_voice_leading(voicings, center_midi=60, spread_min=14)  # missing spread_max and tolerance


def test_generate_voice_leading_center_mode_rejects_combined_modes():
    import pytest
    voicings = [[60, 62, 64, 65, 67, 69]]
    with pytest.raises(ValueError):
        generate_voice_leading(
            voicings,
            min_midi=48, max_midi=72,
            center_midi=60, spread_min=14, spread_max=16, average_tolerance=2,
        )
