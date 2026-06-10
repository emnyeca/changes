# Bundled tool: ireal-musicxml

このディレクトリには、release build に同梱する `ireal-musicxml` の実体を配置します。
実体ファイルは repo に commit しません（`.gitignore` 対象）。
`scripts/PrepareBundledIRealMusicXML.ps1` で取得・配置してください。

## Source

- Package: `@music-i18n/ireal-musicxml`
- Repository: https://github.com/infojunkie/ireal-musicxml
- Author: Karim Ratib (infojunkie)
- License: GPL-3.0-only
- Bundled version: 2.1.1（npm registry tarball から取得）

## 配置後の構成

```text
tools/bundled/ireal-musicxml/
  LICENSE.txt
  package.json
  build/
    ireal-musicxml.mjs   ← 実行に使う self-contained ESM bundle（node_modules 不要）
```

## 実行方法

EUB Changes は upstream CLI（`src/cli/cli.js`）を使いません。
upstream CLI は devDependencies（`sanitize-filename`, `validate-with-xmllint`）を import するため、
production 配置では動作しないためです。

代わりに `tools/eub-ireal-wrapper.mjs` が `build/ireal-musicxml.mjs` を直接 import します。
呼び出し契約は `src/changes/importers/ireal_converter.py` を参照してください。
