# 生成 Artifact ポリシー

`out/digitone-track8/` 配下の generated validation artifact は、active release-candidate development 中の review と reproducibility のために現在は保持します。

これは現時点では意図的な扱いです。

workflow が現在の RC phase を越えて安定した時点で、削除または移動を検討します。

現在保持する artifact:

- `changes_track8_export.events.yaml`
- `changes_track8_export.syx`
- `changes_track8_export_manifest.md`

保持した `.syx` artifact の推奨 validation command:

- `changes check digitone-syx --syx out/digitone-track8/changes_track8_export.syx`

保持した artifact set の推奨 manifest-aware validation command:

- `changes check digitone-syx --syx out/digitone-track8/changes_track8_export.syx --manifest out/digitone-track8/changes_track8_export_manifest.md`

これらの artifact は source of truth ではありません。

Source of truth:

- SongModel YAML input
- export code
- validation logs

generated artifact を permanent release asset として扱わないでください。
