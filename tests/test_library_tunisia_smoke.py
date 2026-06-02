import json
from pathlib import Path

import pytest

from changes.app_settings import AppSettings
from changes.models.song_model import song_model_from_dict
from changes.ui_pipeline import compile_song_for_ui


_TUNISIA_PATH = Path(r"C:\Users\emnye\EUBChanges\library\A Night In Tunisia.song.json")


@pytest.mark.skipif(not _TUNISIA_PATH.exists(), reason="local A Night In Tunisia SongModel not present")
def test_local_a_night_in_tunisia_preview_pipeline_handles_gm7b5() -> None:
    song = song_model_from_dict(json.loads(_TUNISIA_PATH.read_text(encoding="utf-8")))

    compiled = compile_song_for_ui(song, AppSettings())

    assert compiled.timeline.events
