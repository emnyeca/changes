# EUB Changes リリースチェックリスト

## 1. バージョン更新

- [ ] `pyproject.toml` — `version = "X.Y.Z"`
- [ ] `src/changes/main_ui.py` — `_APP_VERSION = "vX.Y.Z"`
- [ ] `src/changes/main_ui.py` — `_APP_BUILD_METADATA` を適切なリリース名に更新
- [ ] `README.md` の License セクションのバージョン表記を更新

## 2. テスト

- [ ] `python -m pytest -q` が全テスト通過

## 3. Bundled ツールのステージング

- [ ] `.\scripts\PrepareBundledIRealMusicXML.ps1 -IncludeNode` を実行
- [ ] `tools\bundled\ireal-musicxml\build\ireal-musicxml.mjs` が存在する
- [ ] `tools\bundled\node\node.exe` が存在する
- [ ] `tools\bundled\node\LICENSE` が存在する

## 4. ビルド前検証

- [ ] `python scripts\verify_desktop_build.py` が全チェック通過
  - `THIRD_PARTY_NOTICES.md` の存在確認
  - bundled ireal-musicxml の存在確認
  - `node.exe` と `node/LICENSE` の存在確認
  - `digitone_syx_toolkit` のインポート確認

## 5. Desktop ビルド（事前確認）

- [ ] `.\scripts\BuildDesktop.ps1` が正常完了
- [ ] 生成された exe を起動してUIが表示されることを確認
- [ ] exe 内に `LICENSE`、`THIRD_PARTY_NOTICES.md`、`tools/bundled/node/LICENSE` が含まれていることを確認

## 6. feature/develop から main へのマージ

- [ ] `feature/develop -> main` のPRを確認
- [ ] PRの差分が今回リリース対象の変更だけであることを確認
- [ ] PRのCI / tests が通っていることを確認
- [ ] PRを `main` にマージ
- [ ] ローカルの `main` を更新

```powershell
git checkout main
git pull origin main
```

- [ ] `main` がクリーンであることを確認

```powershell
git status
```

## 7. main 上で最終ビルド

- [ ] `main` 上で `python -m pytest -q` を再実行
- [ ] `main` 上で `.\scripts\PrepareBundledIRealMusicXML.ps1 -IncludeNode` を再実行
- [ ] `main` 上で `python scripts\verify_desktop_build.py` を再実行
- [ ] `main` 上で `.\scripts\BuildDesktop.ps1` を実行し、Release用exeを生成
- [ ] 生成された exe を起動してUIが表示されることを確認

## 8. GitHub タグ作成

- [ ] `git tag vX.Y.Z` でタグを作成
- [ ] `git push origin vX.Y.Z` でタグをプッシュ

## 9. GitHub Release 作成

- [ ] GitHub Releases ページで新規リリースを作成
- [ ] タグ `vX.Y.Z` を選択
- [ ] リリースノートを記載（主な変更点、既知の制限）
- [ ] ビルドした exe を asset として添付

## 10. GPL 対応ソースの提供

- [ ] GPL v3 の "corresponding source" 要件を満たすこと
- [ ] 同一リリースタグのソースアーカイブ（GitHub の "Source code" zip/tar.gz）が対応ソースとして機能することを確認
- [ ] Release ページの Source code リンクが正しいタグを指していることを確認
- [ ] リリースノートに、対応ソースが同一リリースタグから入手できることを記載

## 11. サードパーティ通知の確認

- [ ] `THIRD_PARTY_NOTICES.md` が最新の bundled ソフトウェアを反映していることを確認
- [ ] bundled Node.js バージョンが `tools/bundled/node/LICENSE` に記載されたバージョンと一致することを確認
- [ ] ireal-musicxml のバージョンが `THIRD_PARTY_NOTICES.md` の記載と一致することを確認
