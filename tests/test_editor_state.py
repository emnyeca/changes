"""Tests for EditorState operations."""

from __future__ import annotations

import pytest

from changes.editor import EditorState


def test_initial_state():
    s = EditorState()
    assert s.title == "NO TITLE"
    assert s.tempo == 120
    assert s.meter == "4/4"
    assert s.cells == []
    assert s.cursor == 0


def test_insert_appends_at_cursor_and_advances():
    s = EditorState()
    s.insert("Cmaj7")
    assert s.cells == ["Cmaj7"]
    assert s.cursor == 1

    s.insert("G7")
    assert s.cells == ["Cmaj7", "G7"]
    assert s.cursor == 2


def test_insert_at_middle_position():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=1)
    s.insert("Am7")
    assert s.cells == ["Cmaj7", "Am7", "G7"]
    assert s.cursor == 2


def test_delete_removes_token_before_cursor():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=2)
    s.delete()
    assert s.cells == ["Cmaj7"]
    assert s.cursor == 1


def test_delete_at_cursor_zero_does_nothing():
    s = EditorState(cells=["Cmaj7"], cursor=0)
    s.delete()
    assert s.cells == ["Cmaj7"]
    assert s.cursor == 0


def test_move_left_decrements_cursor():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=2)
    s.move_left()
    assert s.cursor == 1
    s.move_left()
    assert s.cursor == 0
    s.move_left()
    assert s.cursor == 0  # clamped


def test_move_right_increments_cursor():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=0)
    s.move_right()
    assert s.cursor == 1
    s.move_right()
    assert s.cursor == 2
    s.move_right()
    assert s.cursor == 2  # clamped


def test_undo_reverts_insert():
    s = EditorState()
    s.insert("Cmaj7")
    s.insert("G7")
    s.undo()
    assert s.cells == ["Cmaj7"]
    assert s.cursor == 1


def test_undo_reverts_delete():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=2)
    s.delete()
    s.undo()
    assert s.cells == ["Cmaj7", "G7"]
    assert s.cursor == 2


def test_undo_on_empty_history_does_nothing():
    s = EditorState(cells=["Cmaj7"])
    s.undo()
    assert s.cells == ["Cmaj7"]


def test_clear_empties_cells_and_resets_cursor():
    s = EditorState(cells=["Cmaj7", "|", "G7"], cursor=2)
    s.clear()
    assert s.cells == []
    assert s.cursor == 0


def test_clear_is_undoable():
    s = EditorState(cells=["Cmaj7", "G7"], cursor=2)
    s.clear()
    s.undo()
    assert s.cells == ["Cmaj7", "G7"]
    assert s.cursor == 2
