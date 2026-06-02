"""MusicXML form expansion: repeats, 1st/2nd endings, D.S./D.C. al Coda.

Pipeline:
  ImportedSong (bars + raw_form_markers)
  -> build per-measure annotations
  -> pair repeat blocks (start/end/endings)
  -> execute playback expansion
  -> assign section_ids
  -> FormExpansionResult
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction

from changes.importers.musicxml import ImportedBar, ImportedSong, RawFormMarker


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FormExpansionResult:
    bars: tuple[ImportedBar, ...]
    section_ids: tuple[str | None, ...]
    source_measure_count: int
    playback_measure_count: int
    warnings: tuple[str, ...]
    diagnostics: tuple[str, ...]


class FormExpansionError(ValueError):
    """Raised when form expansion would produce wrong results."""


# ── Per-measure annotation ────────────────────────────────────────────────────

@dataclass
class _Ann:
    idx: int
    number: str
    repeat_forward: bool = False
    repeat_backward: bool = False
    repeat_times: int = 2
    ending_starts: frozenset = field(default_factory=frozenset)
    ending_stops: frozenset = field(default_factory=frozenset)
    has_segno: bool = False
    has_coda: bool = False       # <coda/> or sound.coda
    has_tocoda: bool = False     # words "To Coda", sound.tocoda, or inferred
    is_ds: bool = False          # D.S. al Coda instruction
    is_dc: bool = False          # D.C. al Coda instruction
    rehearsal: str | None = None
    double_barline_left: bool = False
    double_barline_right: bool = False
    words: list = field(default_factory=list)


# ── Repeat block info ─────────────────────────────────────────────────────────

@dataclass
class _RepeatBlock:
    start_idx: int
    end_idx: int            # position of repeat_backward
    times: int              # total times to play
    first_ending_start: int | None  # first idx of 1st ending (or None)


# ── Regex patterns ────────────────────────────────────────────────────────────

_RE_NX = re.compile(r'\b(\d+)\s*[xX]\b')
_RE_DS = re.compile(r'D\.?\s*S\.?\s*al\s+Coda', re.IGNORECASE)
_RE_DC = re.compile(r'D\.?\s*C\.?\s*al\s+Coda', re.IGNORECASE)
_RE_TOCODA = re.compile(r'To\s+Coda', re.IGNORECASE)


# ── Build annotations ─────────────────────────────────────────────────────────

def _build_annotations(
    bars: list[ImportedBar],
    markers_by_number: dict[str, list[RawFormMarker]],
) -> list[_Ann]:
    anns: list[_Ann] = []
    for idx, bar in enumerate(bars):
        ann = _Ann(idx=idx, number=bar.source_measure_number)
        for m in markers_by_number.get(bar.source_measure_number, []):
            mt = m.marker_type
            p = m.raw_payload
            if mt == "repeat":
                if p.get("direction") == "forward":
                    ann.repeat_forward = True
                elif p.get("direction") == "backward":
                    ann.repeat_backward = True
                    ann.repeat_times = int(p.get("normalized_times") or "2")
            elif mt == "ending":
                try:
                    num = int(str(p.get("number", "")).split(".")[0].strip())
                except (ValueError, AttributeError):
                    num = 0
                etype = str(p.get("type", ""))
                if etype in ("start",):
                    ann.ending_starts = ann.ending_starts | frozenset({num})
                elif etype in ("stop", "discontinue"):
                    ann.ending_stops = ann.ending_stops | frozenset({num})
            elif mt in ("segno", "sound_segno"):
                ann.has_segno = True
            elif mt in ("coda", "sound_coda"):
                ann.has_coda = True
            elif mt in ("tocoda", "sound_tocoda"):
                ann.has_tocoda = True
            elif mt == "words":
                text = str(p.get("text", ""))
                ann.words.append(text)
                if _RE_DS.search(text):
                    ann.is_ds = True
                if _RE_DC.search(text):
                    ann.is_dc = True
                if _RE_TOCODA.search(text):
                    ann.has_tocoda = True
            elif mt in ("sound_dalsegno",):
                ann.is_ds = True
            elif mt in ("sound_dacapo",):
                ann.is_dc = True
            elif mt == "double_barline":
                loc = str(p.get("location", "right"))
                if loc == "left":
                    ann.double_barline_left = True
                else:
                    ann.double_barline_right = True
            elif mt == "rehearsal":
                ann.rehearsal = str(p.get("text", "")).strip() or None
        anns.append(ann)
    return anns


# ── Pair repeat blocks ────────────────────────────────────────────────────────

def _pair_repeat_blocks(anns: list[_Ann]) -> dict[int, _RepeatBlock]:
    """Returns {backward_idx: _RepeatBlock}."""
    stack: list[int] = []
    blocks: dict[int, _RepeatBlock] = {}

    for ann in anns:
        if ann.repeat_forward:
            stack.append(ann.idx)
        if ann.repeat_backward:
            start_idx = stack.pop() if stack else 0
            times = ann.repeat_times
            # Words override (e.g. "5x")
            for w in ann.words:
                m = _RE_NX.search(w)
                if m:
                    times = int(m.group(1))
                    break
            # Also check adjacent previous measure for words
            if ann.idx > 0 and ann.idx - 1 < len(anns):
                prev = anns[ann.idx - 1]
                for w in prev.words:
                    m = _RE_NX.search(w)
                    if m:
                        times = max(times, int(m.group(1)))
                        break
            # Find first ending start within this block
            first_ending_start: int | None = None
            for j in range(start_idx, ann.idx + 1):
                if 1 in anns[j].ending_starts:
                    first_ending_start = j
                    break
            blocks[ann.idx] = _RepeatBlock(
                start_idx=start_idx,
                end_idx=ann.idx,
                times=times,
                first_ending_start=first_ending_start,
            )
    return blocks


# ── Coda inference for iRealPro ───────────────────────────────────────────────

def _infer_coda_positions(
    anns: list[_Ann],
) -> tuple[int | None, int | None]:
    """Returns (tocoda_idx, coda_target_idx).

    For iRealPro: when multiple <coda/> markers exist, infer based on
    position relative to the D.S./D.C. instruction.
    For ireal-musicxml: tocoda comes from words/sound.tocoda, coda from <coda/>.
    """
    ds_dc_idx: int | None = None
    coda_positions: list[int] = []
    tocoda_positions: list[int] = []
    segno_idx: int | None = None

    for ann in anns:
        if ann.has_segno and segno_idx is None:
            segno_idx = ann.idx
        if (ann.is_ds or ann.is_dc) and ds_dc_idx is None:
            ds_dc_idx = ann.idx
        if ann.has_coda:
            coda_positions.append(ann.idx)
        if ann.has_tocoda:
            tocoda_positions.append(ann.idx)

    if not coda_positions:
        return (tocoda_positions[0] if tocoda_positions else None, None)

    if len(coda_positions) == 1:
        # Single coda marker = coda target; tocoda from explicit markers
        coda_target_idx = coda_positions[0]
        tocoda_idx = tocoda_positions[0] if tocoda_positions else None
        # If no explicit tocoda, but no ds/dc either, coda target is just a section marker
        return tocoda_idx, coda_target_idx

    # Multiple coda markers: apply iRealPro inference
    if ds_dc_idx is not None:
        # First coda before ds_dc = To Coda; last coda at/after ds_dc = target
        before = [i for i in coda_positions if i < ds_dc_idx]
        after = [i for i in coda_positions if i >= ds_dc_idx]
        tocoda_idx = before[0] if before else None
        coda_target_idx = after[-1] if after else coda_positions[-1]
        # Explicit tocoda markers take precedence
        if tocoda_positions:
            tocoda_idx = tocoda_positions[0]
        return tocoda_idx, coda_target_idx
    else:
        # No D.S./D.C.: last coda = section marker, first = cosmetic
        coda_target_idx = coda_positions[-1]
        tocoda_idx = tocoda_positions[0] if tocoda_positions else None
        return tocoda_idx, coda_target_idx


def _find_segno_ds_dc(anns: list[_Ann]) -> tuple[int | None, int | None, int | None]:
    """Returns (segno_idx, ds_idx, dc_idx)."""
    segno_idx = ds_idx = dc_idx = None
    for ann in anns:
        if ann.has_segno and segno_idx is None:
            segno_idx = ann.idx
        if ann.is_ds and ds_idx is None:
            ds_idx = ann.idx
        if ann.is_dc and dc_idx is None:
            dc_idx = ann.idx
    return segno_idx, ds_idx, dc_idx


# ── Expansion executor ────────────────────────────────────────────────────────

@dataclass
class _RepeatState:
    block: _RepeatBlock
    current_pass: int = 1


def _execute_expansion(
    bars: list[ImportedBar],
    anns: list[_Ann],
    blocks: dict[int, _RepeatBlock],
    segno_idx: int | None,
    tocoda_idx: int | None,
    coda_target_idx: int | None,
    ds_idx: int | None,
    dc_idx: int | None,
) -> tuple[list[int], list[str], list[str]]:
    """Execute form expansion. Returns (source_indices, warnings, diagnostics)."""
    has_ds_dc = (ds_idx is not None) or (dc_idx is not None)

    # Validate
    if has_ds_dc:
        if (ds_idx is not None) and segno_idx is None:
            raise FormExpansionError("D.S. al Coda found but no Segno marker")
        if coda_target_idx is None:
            raise FormExpansionError("D.S./D.C. al Coda found but no Coda target")
        if tocoda_idx is None:
            raise FormExpansionError("D.S./D.C. al Coda found but no To Coda marker")

    result: list[int] = []
    warnings: list[str] = []
    diagnostics: list[str] = []

    repeat_stack: list[_RepeatState] = []
    ds_done = False      # D.S./D.C. has been executed
    ds_pass = False      # currently in post-D.S./D.C. no-repeat pass
    pending_ds = False   # D.S. encountered inside repeat, deferred
    pending_dc = False   # D.C. encountered inside repeat, deferred

    pos = 0
    safety = 0
    max_iters = len(bars) * 100

    while pos < len(bars):
        safety += 1
        if safety > max_iters:
            warnings.append("Form expansion safety limit reached; expansion truncated")
            break

        ann = anns[pos]

        # ── In D.S./D.C. pass: linear play, no repeats ─────────────────────
        if ds_pass:
            # Emit this measure (linear — no repeat jumps)
            result.append(pos)
            # Check To Coda trigger (must be before repeat_backward skip so that
            # measures carrying both repeat_backward AND has_tocoda trigger correctly)
            if tocoda_idx is not None and pos == tocoda_idx:
                diagnostics.append(f"To Coda at m{ann.number} → jump to Coda")
                pos = coda_target_idx
                ds_pass = False
                continue
            # Skip repeat_backward action (just advance)
            pos += 1
            continue

        # ── Normal play ───────────────────────────────────────────────────

        # Repeat forward: push only on first visit (not on repeat jumps back)
        if ann.repeat_forward:
            if not ds_pass:
                already_tracking = any(rs.block.start_idx == pos for rs in repeat_stack)
                if not already_tracking:
                    block = None
                    for b in blocks.values():
                        if b.start_idx == pos:
                            block = b
                            break
                    if block is not None:
                        repeat_stack.append(_RepeatState(block=block, current_pass=1))
            # Emit and continue
            result.append(pos)
            pos += 1
            continue

        # D.S. instruction
        if ann.is_ds and not ds_done and not pending_ds and not pending_dc:
            if repeat_stack:
                pending_ds = True
            else:
                ds_done = True
                ds_pass = True
                result.append(pos)
                target = segno_idx if segno_idx is not None else 0
                diagnostics.append(f"D.S. at m{ann.number} → jump to segno m{anns[target].number}")
                pos = target
                continue

        # D.C. instruction
        if ann.is_dc and not ds_done and not pending_ds and not pending_dc:
            if repeat_stack:
                pending_dc = True
            else:
                ds_done = True
                ds_pass = True
                result.append(pos)
                diagnostics.append(f"D.C. at m{ann.number} → jump to beginning")
                pos = 0
                continue

        # 1st ending skip on last pass (must be checked before repeat_backward)
        if (
            repeat_stack
            and ann.ending_starts
            and 1 in ann.ending_starts
            and 2 not in ann.ending_starts
            and repeat_stack[-1].current_pass == repeat_stack[-1].block.times
        ):
            # Last pass: skip the 1st ending (and its repeat_backward) entirely
            end_idx = repeat_stack[-1].block.end_idx
            repeat_stack.pop()
            if pending_ds and not ds_done:
                pending_ds = False
                ds_done = True
                ds_pass = True
                target = segno_idx if segno_idx is not None else 0
                pos = target
                continue
            elif pending_dc and not ds_done:
                pending_dc = False
                ds_done = True
                ds_pass = True
                pos = 0
                continue
            pos = end_idx + 1
            continue

        # Repeat backward
        if ann.repeat_backward:
            result.append(pos)

            if repeat_stack:
                rs = repeat_stack[-1]
                if rs.current_pass < rs.block.times:
                    # More passes: jump back
                    rs.current_pass += 1
                    pos = rs.block.start_idx
                    continue
                else:
                    # Last pass: exit repeat
                    repeat_stack.pop()
                    # Execute pending D.S./D.C.
                    if pending_ds and not ds_done:
                        pending_ds = False
                        ds_done = True
                        ds_pass = True
                        target = segno_idx if segno_idx is not None else 0
                        diagnostics.append(f"Deferred D.S. executes after repeat → jump to m{anns[target].number}")
                        pos = target
                        continue
                    elif pending_dc and not ds_done:
                        pending_dc = False
                        ds_done = True
                        ds_pass = True
                        diagnostics.append("Deferred D.C. executes after repeat → jump to beginning")
                        pos = 0
                        continue
                    pos += 1
                    continue
            else:
                warnings.append(f"m{ann.number}: repeat backward without matching forward, skipping")
                pos += 1
                continue
            continue

        # Normal emit
        result.append(pos)
        pos += 1

    return result, warnings, diagnostics


# ── Section label assignment ──────────────────────────────────────────────────

_KNOWN_LABEL_MAP: dict[str, str] = {
    "intro": "INT", "introduction": "INT", "intro.": "INT",
    "coda": "COD", "cod": "COD", "coda.": "COD",
    "bridge": "BRG", "brdg": "BRG", "brig": "BRG",
    "outro": "OUT", "end": "OUT", "ending": "OUT", "fine": "OUT",
    "verse": "VRS", "vrs": "VRS",
    "chorus": "CHO", "cho": "CHO",
    "theme": "THM",
    "head": "HD",
    "solo": "SOL",
    "interlude": "ITL",
    "vamp": "VMP",
}


def _shorten_label(label: str) -> str:
    """Convert rehearsal label to an abbreviated section prefix for section_id.

    Known words (intro, coda, bridge, ...) → fixed 2-3 char abbreviation.
    Single letter (A, B, C) → kept as-is.
    Other labels → uppercased ASCII, truncated to 3 chars.
    """
    raw = label.strip()
    if not raw:
        return "S"
    mapped = _KNOWN_LABEL_MAP.get(raw.lower())
    if mapped is not None:
        return mapped
    # Single letter: keep as-is
    if len(raw) == 1 and raw.isalpha():
        return raw.upper()
    # Multi-char: normalize to uppercase ASCII, truncate to 3 chars
    normalized = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    return normalized[:3] if normalized else "S"


def _assign_section_ids(
    source_indices: list[int],
    anns: list[_Ann],
    coda_target_idx: int | None,
    next_section_after: set[int],
) -> list[str | None]:
    """Assign section_ids for each expanded bar.

    A new section starts when:
    - A rehearsal mark is present (highest priority)
    - The bar is the coda target
    - A double_barline@left is on this bar
    - The previous bar had double_barline@right
    - First bar of the song (auto-label "S1")
    """
    label_counts: dict[str, int] = {}
    current_label: str | None = None
    ids: list[str | None] = []
    prev_source_idx: int | None = None

    for expanded_pos, src_idx in enumerate(source_indices):
        ann = anns[src_idx]

        is_new_section = False
        new_label: str | None = None

        # Priority: rehearsal > coda target > structural_repeat_forward > double_barline > first_bar
        #
        # "Structural" repeat_forward: at the very start of the song, or immediately
        # following a repeat_backward or double_barline@right in the source.  This
        # avoids creating spurious section splits for in-section repeats.
        _prev_is_section_end = (
            src_idx > 0
            and (
                anns[src_idx - 1].repeat_backward
                or anns[src_idx - 1].double_barline_right
            )
        )
        if ann.rehearsal:
            new_label = _shorten_label(ann.rehearsal)
            is_new_section = True
        elif coda_target_idx is not None and src_idx == coda_target_idx:
            new_label = "COD"
            is_new_section = True
        elif ann.repeat_forward and (src_idx == 0 or _prev_is_section_end):
            is_new_section = True
        elif ann.double_barline_left:
            is_new_section = True
        elif prev_source_idx is not None and prev_source_idx in next_section_after:
            is_new_section = True

        # Auto-start first section at the very beginning
        if not is_new_section and current_label is None and expanded_pos == 0:
            is_new_section = True

        if is_new_section:
            base = new_label if new_label else "S"
            label_counts[base] = label_counts.get(base, 0) + 1
            current_label = f"{base}{label_counts[base]}"

        ids.append(current_label)
        prev_source_idx = src_idx

    return ids


# ── Main entry point ──────────────────────────────────────────────────────────

def expand_form(imported: ImportedSong) -> FormExpansionResult:
    """Expand MusicXML form markers into a playback-order bar sequence.

    Returns a FormExpansionResult with expanded bars and per-bar section_ids.
    If no form markers are present, returns bars in source order with section_ids=None.
    """
    bars = list(imported.bars)
    if not bars:
        return FormExpansionResult(
            bars=tuple(),
            section_ids=tuple(),
            source_measure_count=0,
            playback_measure_count=0,
            warnings=(),
            diagnostics=(),
        )

    # Group markers by measure number
    markers_by_number: dict[str, list[RawFormMarker]] = {}
    for m in imported.raw_form_markers:
        markers_by_number.setdefault(m.measure_number, []).append(m)

    # Build annotations
    anns = _build_annotations(bars, markers_by_number)

    # Check if there are any form markers worth expanding
    has_repeats = any(a.repeat_backward for a in anns)
    has_ds_dc = any(a.is_ds or a.is_dc for a in anns)

    # Pair repeat blocks
    blocks = _pair_repeat_blocks(anns)

    # Find special positions
    segno_idx, ds_instruction_idx, dc_instruction_idx = _find_segno_ds_dc(anns)
    tocoda_idx, coda_target_idx = _infer_coda_positions(anns)

    # Expand
    try:
        source_indices, warnings, diagnostics = _execute_expansion(
            bars=bars,
            anns=anns,
            blocks=blocks,
            segno_idx=segno_idx,
            tocoda_idx=tocoda_idx,
            coda_target_idx=coda_target_idx,
            ds_idx=ds_instruction_idx,
            dc_idx=dc_instruction_idx,
        )
    except FormExpansionError as exc:
        return FormExpansionResult(
            bars=tuple(bars),
            section_ids=tuple(None for _ in bars),
            source_measure_count=len(bars),
            playback_measure_count=len(bars),
            warnings=(
                f"Form expansion failed; imported source order without playback expansion: {exc}",
            ),
            diagnostics=(),
        )

    # Find measures where dbl@right of that bar → next bar starts a new section
    next_section_after: set[int] = set()
    for ann in anns:
        if ann.double_barline_right:
            next_section_after.add(ann.idx)

    # Assign section IDs
    section_ids = _assign_section_ids(
        source_indices=source_indices,
        anns=anns,
        coda_target_idx=coda_target_idx,
        next_section_after=next_section_after,
    )

    expanded_bars = tuple(bars[i] for i in source_indices)
    expanded_ids = tuple(section_ids)

    diag_summary = (
        f"source={len(bars)} measures, playback={len(expanded_bars)} measures"
        + (f", repeats expanded" if has_repeats else "")
        + (f", D.S./D.C. resolved" if has_ds_dc else "")
    )
    diagnostics = [diag_summary] + diagnostics

    return FormExpansionResult(
        bars=expanded_bars,
        section_ids=expanded_ids,
        source_measure_count=len(bars),
        playback_measure_count=len(expanded_bars),
        warnings=tuple(warnings),
        diagnostics=tuple(diagnostics),
    )
