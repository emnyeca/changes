# Repository 統合方針

## 目的

この文書は、`changes` と `digitone-syx-toolkit` の現在の repository 方針を定義します。

## 現在の判断

- repository は分離したまま維持する。
- dependency direction は `changes -> digitone-syx-toolkit` の一方向にする。
- `changes` runtime path では toolkit integration を明示的かつ lazy に保つ。
- musical model layer に low-level Digitone encoding logic を重複実装しない。

## toolkit に求める capability

- events YAML loading / validation
- events YAML からの SysEx build
- Digitone template seed handling
- per-track scale handling
- track default velocity propagation

## 責務境界

`changes` 側に置く責務:

- musical allocation / rendering
- export orchestration / artifact policy
- send/check command safety policy

`digitone-syx-toolkit` 側に置く責務:

- byte-level SysEx encoding
- checksum / packing details
- template byte handling
- hardware-specific low-level builder behavior

## repository 分離中の CI policy

- normal test は toolkit install を必須にしない。
- toolkit-dependent integration test は専用 CI job で実行する。
- local development では両 repository を editable install して integration test を実行できる。

## migration 判断基準

次の多くが成立する場合のみ、より強い repository integration を検討する。

- integration test を every PR の required check にする必要がある。
- schema change が頻繁に両 repository をまたぐ。
- product packaging がより強い repository coupling を必要とする。
- 現在の two-repo overhead が migration cost を上回る。

## rollback 方針

将来 repository topology を変更する場合も、package import boundary を保ち、migration 中は public toolkit API を安定させて rollback 可能性を維持する。

## scope boundary

この文書は現在の方針のみを定義します。runtime behavior は変更しません。
