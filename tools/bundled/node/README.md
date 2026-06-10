# Bundled tool: Node.js portable runtime

このディレクトリには、release build に同梱する portable Node.js runtime（`node.exe` と LICENSE）を配置します。
実体ファイルは repo に commit しません（`.gitignore` 対象）。
`scripts/PrepareBundledIRealMusicXML.ps1 -IncludeNode` で取得・配置してください。

## 配置後の構成

```text
tools/bundled/node/
  node.exe
  LICENSE        ← Node.js distribution の LICENSE
```

## 用途

同梱した `ireal-musicxml` converter（`tools/eub-ireal-wrapper.mjs`）の実行にのみ使用します。

開発環境では PATH 上の `node` が fallback として使われるため、配置は必須ではありません。
環境変数 `EUB_CHANGES_NODE_EXE` で明示指定もできます。
