"""EditorState: lightweight GUI input model for chord progression entry.

Holds the cell sequence (chord tokens, %, |, ||), cursor position, and
metadata. Does not contain any rendering or export logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EditorState:
    """Mutable GUI state for the chord progression editor.

    cells contains a flat sequence of tokens:
      - chord symbol strings (e.g. "Cmaj7", "G7")
      - "%" — repeat previous chord cell
      - "|" — measure boundary (barline)
      - "||" — section boundary (also acts as barline)

    cursor is an index into cells (0 = before all cells,
    len(cells) = after all cells).
    """

    title: str = "NO TITLE"
    tempo: int = 120
    meter: str = "4/4"
    working_key: str = "C"
    composer: str | None = None
    cells: list[str] = field(default_factory=list)
    cursor: int = 0
    _history: list[tuple[list[str], int]] = field(
        default_factory=list, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Mutation helpers

    def _snapshot(self) -> None:
        self._history.append((list(self.cells), self.cursor))

    def insert(self, token: str) -> None:
        self._snapshot()
        self.cells.insert(self.cursor, token)
        self.cursor += 1

    def delete(self) -> None:
        """Delete the token immediately before the cursor (backspace)."""
        if self.cursor > 0:
            self._snapshot()
            self.cells.pop(self.cursor - 1)
            self.cursor -= 1

    def move_left(self) -> None:
        self.cursor = max(0, self.cursor - 1)

    def move_right(self) -> None:
        self.cursor = min(len(self.cells), self.cursor + 1)

    def undo(self) -> None:
        if self._history:
            cells, cursor = self._history.pop()
            self.cells = cells
            self.cursor = cursor

    def clear(self) -> None:
        self._snapshot()
        self.cells.clear()
        self.cursor = 0
