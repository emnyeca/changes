import pytest
from fractions import Fraction

from changes.models.rendered_arrangement import (
    RenderedArrangement,
    RenderedHarmonyOccurrence,
    RenderedChordLayer,
    RenderedCloudLayer,
    RenderedBassLayer,
    RenderedLayerNote,
    rendered_arrangement_to_dict,
    rendered_arrangement_from_dict,
)


def test_single_chord_only_arrangement():
    # create chord-only arrangement with one occurrence
    chord_notes = tuple(
        RenderedLayerNote(note_midi=midi, velocity=vel, lane_id=f"chord_note_{i+1}", diagnostics=("diag",))
        for i, (midi, vel) in enumerate([(60, 70), (64, 70), (67, 70), (71, 50), (74, 70), (78, 50)])
    )
    chord_layer = RenderedChordLayer(
        role="chord",
        source_pitch_classes=(0, 4, 7, 11, 2, 9),
        canonical_stacked_midi_notes=(48, 52, 55, 59, 62, 69),
        realized_midi_notes=(48, 52, 55, 59, 62, 69),
        velocities=(70, 70, 70, 50, 70, 50),
        length_mode="explicit_event_length",
        notes=chord_notes,
        diagnostics=("chord diagnostic",),
    )
    occ = RenderedHarmonyOccurrence(
        id="occ1",
        source_harmony_id="h1",
        symbol="Cmaj7",
        onset_quarters=Fraction(0, 1),
        duration_quarters=Fraction(4, 1),
        chord=chord_layer,
        diagnostics=("occ diagnostic",),
    )
    arr = RenderedArrangement(
        title="Test",
        performance_tempo=Fraction(120, 1),
        occurrences=(occ,),
        diagnostics=("arr diagnostic",),
    )
    # Ensure created object has chord and no cloud or bass
    assert arr.occurrences[0].chord is chord_layer
    assert arr.occurrences[0].cloud is None
    assert arr.occurrences[0].bass is None


def test_full_layer_arrangement():
    # create cloud layer with six notes
    cloud_notes = tuple(
        RenderedLayerNote(note_midi=60 + i, velocity=80, lane_id=f"cloud_voice_{i+1}")
        for i in range(6)
    )
    cloud_layer = RenderedCloudLayer(
        role="cloud",
        notes=cloud_notes,
        diagnostics=("cloud diag",),
    )
    # chord layer similar to previous but with different values
    chord_notes = tuple(
        RenderedLayerNote(note_midi=50 + i * 2, velocity=60, lane_id=f"chord_note_{i+1}")
        for i in range(6)
    )
    chord_layer = RenderedChordLayer(
        role="chord",
        source_pitch_classes=(11, 2, 4, 7, 9, 0),
        canonical_stacked_midi_notes=(59, 63, 66, 70, 73, 80),
        realized_midi_notes=(58, 59, 61, 63, 66, 68),
        velocities=(70, 70, 70, 50, 70, 50),
        length_mode="inherit",
        notes=chord_notes,
        diagnostics=("chord diag",),
    )
    # bass layer
    bass_note = RenderedLayerNote(note_midi=36, velocity=90, lane_id="bass")
    bass_layer = RenderedBassLayer(
        role="bass",
        note=bass_note,
        source_pitch_class=0,
        diagnostics=("bass diag",),
    )
    occ = RenderedHarmonyOccurrence(
        id="occ2",
        source_harmony_id="h2",
        symbol="Am9",
        onset_quarters=Fraction(4, 1),
        duration_quarters=Fraction(4, 1),
        cloud=cloud_layer,
        chord=chord_layer,
        bass=bass_layer,
    )
    arr = RenderedArrangement(
        title="Full Test",
        performance_tempo=Fraction(100, 1),
        occurrences=(occ,),
    )
    # check layering
    assert arr.occurrences[0].cloud is cloud_layer
    assert len(arr.occurrences[0].cloud.notes) == 6
    assert arr.occurrences[0].bass is bass_layer


def test_dict_includes_version_and_type():
    # simple arrangement
    arr = RenderedArrangement(
        title="Simple",
        performance_tempo=Fraction(120, 1),
        occurrences=(),
    )
    d = rendered_arrangement_to_dict(arr)
    assert d["version"] == 1
    assert d["type"] == "rendered_arrangement"


def test_fraction_roundtrip_and_missing_layers():
    chord_layer = RenderedChordLayer(
        role="chord",
        source_pitch_classes=(0, 4, 7, 11, 2, 9),
        canonical_stacked_midi_notes=(48, 52, 55, 59, 62, 69),
        realized_midi_notes=(48, 52, 55, 59, 62, 69),
        velocities=(70, 70, 70, 50, 70, 50),
        length_mode="explicit_event_length",
        notes=tuple(RenderedLayerNote(note_midi=48 + i * 2) for i in range(6)),
    )
    occ = RenderedHarmonyOccurrence(
        id="occ3",
        source_harmony_id="h3",
        symbol="Cmaj7",
        onset_quarters=Fraction(1, 3),
        duration_quarters=Fraction(8, 3),
        chord=chord_layer,
    )
    arr = RenderedArrangement(
        title="FracTest",
        performance_tempo=Fraction(90, 1),
        occurrences=(occ,),
    )
    d = rendered_arrangement_to_dict(arr)
    restored = rendered_arrangement_from_dict(d)
    # Fractions round-trip
    assert restored.occurrences[0].onset_quarters == Fraction(1, 3)
    assert restored.occurrences[0].duration_quarters == Fraction(8, 3)
    assert restored.performance_tempo == Fraction(90, 1)
    # missing layers remain None
    assert restored.occurrences[0].cloud is None
    assert restored.occurrences[0].bass is None


def test_chord_bass_cloud_fields_preserved_and_tuple_types():
    # Setup for verifying preserved fields
    chord_notes = tuple(
        RenderedLayerNote(note_midi=60 + i, velocity=70) for i in range(6)
    )
    chord_layer = RenderedChordLayer(
        role="chord",
        source_pitch_classes=(0, 4, 7, 11, 2, 9),
        canonical_stacked_midi_notes=(48, 52, 55, 59, 62, 69),
        realized_midi_notes=(48, 52, 55, 59, 62, 69),
        velocities=(70, 70, 70, 50, 70, 50),
        length_mode="inherit",
        notes=chord_notes,
        diagnostics=("chord diag",),
    )
    bass_layer = RenderedBassLayer(
        role="bass",
        note=RenderedLayerNote(note_midi=36, velocity=80),
        source_pitch_class=0,
        diagnostics=("bass diag",),
    )
    cloud_notes = tuple(
        RenderedLayerNote(note_midi=72 + i, velocity=75, lane_id=f"cloud_voice_{i+1}") for i in range(6)
    )
    cloud_layer = RenderedCloudLayer(
        role="cloud",
        notes=cloud_notes,
        diagnostics=("cloud diag",),
    )
    occ = RenderedHarmonyOccurrence(
        id="occ4",
        source_harmony_id="h4",
        symbol="Cmaj7",
        onset_quarters=Fraction(8, 1),
        duration_quarters=Fraction(4, 1),
        cloud=cloud_layer,
        chord=chord_layer,
        bass=bass_layer,
    )
    arr = RenderedArrangement(
        title="Verify",
        performance_tempo=Fraction(140, 1),
        occurrences=(occ,),
        diagnostics=("arr diag",),
    )
    d = rendered_arrangement_to_dict(arr)
    restored = rendered_arrangement_from_dict(d)
    rocc = restored.occurrences[0]
    # Check chord fields
    rc = rocc.chord
    assert rc.source_pitch_classes == chord_layer.source_pitch_classes
    assert rc.canonical_stacked_midi_notes == chord_layer.canonical_stacked_midi_notes
    assert rc.realized_midi_notes == chord_layer.realized_midi_notes
    assert rc.velocities == chord_layer.velocities
    assert rc.length_mode == chord_layer.length_mode
    assert rc.diagnostics == chord_layer.diagnostics
    # Check tuple types
    assert isinstance(rc.source_pitch_classes, tuple)
    assert isinstance(rc.velocities, tuple)
    assert isinstance(rc.notes, tuple)
    # Bass fields
    rb = rocc.bass
    assert rb.note.note_midi == bass_layer.note.note_midi
    assert rb.source_pitch_class == bass_layer.source_pitch_class
    # Cloud
    cl = rocc.cloud
    assert len(cl.notes) == 6
    assert all(isinstance(n, type(cloud_layer.notes[0])) for n in cl.notes)
    assert cl.diagnostics == cloud_layer.diagnostics
