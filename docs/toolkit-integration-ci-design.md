# Toolkit 統合 CI 設計

## 目的

この文書は、`changes` における toolkit-dependent test の現在の CI policy を定義します。

## 現在の CI policy

- core pytest suite は toolkit installation を必須にせず実行する。
- toolkit-dependent test は dedicated integration job で実行する。
- integration job は両 repository を checkout し、両 package を editable install する。

## Toolkit-dependent test scope

現在価値が高い integration check:

- generated events YAML の loader validation
- SysEx byte generation path
- toolkit behavior を必要とする fixture generation path

## Job behavior

- pull request で実行する。
- 特定の toolkit ref を確認する必要がある場合は manual dispatch を許可する。
- speed と clarity のため、normal core test job は分離する。

## Failure policy

- integration job は advisory から開始できる。
- 影響する export path が standard product path になった時点で required check に昇格する。

## Ref policy

- default toolkit ref は drift detection のため main を追従してよい。
- stabilization / release path では reproducibility のため pinned ref を使ってよい。

## Local workflow

From `changes` repository:

```powershell
python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -m pytest tests/test_track8_toolkit_loader_validation.py tests/test_track8_sysex_export.py -q
```

## Scope boundary

この文書は policy と job shape を説明します。この文書自体は workflow や runtime code を変更しません。
