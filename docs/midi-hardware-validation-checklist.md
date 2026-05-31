# MIDI ハードウェア検証チェックリスト

## 目的

この checklist は、Digitone II への real SysEx send を manual validation するためのものです。

最初の manual run preparation は `docs/hardware-validation/digitone-syx-real-send-first-validation.md` を参照してください。

最初の validation では、II-V-I fixture の guarded real-send が passed として記録されています。

## Preconditions

- Digitone II を USB MIDI または MIDI interface で接続している
- Digitone II が MIDI output port として見えている
- Chord export（Digitone Track 8）で生成した既知良好 `.syx`
- 重要な Digitone II data を backup 済み
- pattern data を書き込む risk を明示的に受け入れている
- volume / audio monitoring が安全
- live performance が device state に依存していない

## software preparation

- optional MIDI dependency を install:
  - `pip install .[midi]`
  - or `pip install mido python-rtmidi`
- version check:
  - `python -c "import importlib.metadata as md; print('mido', md.version('mido'))"`
  - `python -c "import importlib.metadata as md; print('python-rtmidi', md.version('python-rtmidi'))"`
- port listing が動くことを確認
- dry-run send が先に動くことを確認
- `.syx` file が `0xF0` で始まり `0xF7` で終わることを確認
- 先に manifest-aware check を行う:
  - `changes check digitone-syx --syx <file.syx> --manifest <file_manifest.md>`

## manual validation steps

1. Chord export（Digitone Track 8）で `.syx` を生成する。
2. dry-run send を実行する。
3. 利用可能な MIDI output port を一覧する。
4. Digitone II port を明示的に選択する。
5. device state を overwrite してよいことを確認する。
6. real-send command で `.syx` を送信する。
7. Digitone II 上で import / transfer を確認する。
8. Track 8 pattern behavior を確認する。
9. 日付付き hardware validation note に結果を記録する。

## stop conditions

次の場合は即時中止する。

- port name が曖昧
- Digitone II が見えない
- 誤った device が SysEx を受信する可能性がある
- `.syx` file が期待した export 由来ではない
- 重要な data を backup していない
- device behavior が期待した import flow と異なる

## result log template

recording template は `docs/hardware-validation/digitone-syx-real-send-template.md` を使います。

practical workflow は `docs/real-send-workflow.md`、CLI reference は `docs/cli.md`、documentation entry point は `docs/index.md` を参照してください。

```text
Date:
Device:
Firmware:
Connection:
OS:
Python:
Backend:
Port name:
SYX file:
Command:
Result:
Observed Digitone behavior:
Track 8 validation:
Issues:
Follow-up:
```
