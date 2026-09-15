# Final Release Checklist

本文件提供 Garmin TCX AI 每次 Windows 版本釋出前、中、後的檢驗與發行步驟。
以下以 `v0.2.0` 為例；發行新版本時，把所有 `0.2.0` 換成新版號即可。

## 0. 版本號

發行前確認以下四處版本號一致，並在 `RELEASE_NOTES.md` 最上方加入該版本的變更說明：

- `pyproject.toml` 的 `version`
- `src/garmin_tcx_ai/__init__.py` 的 `__version__`
- `tests/test_package_import.py` 的版本斷言
- `packaging/version_info.txt` 的 `filevers`、`prodvers`、`FileVersion`、`ProductVersion`

---

## 1. Release 前準備

請在 Windows 本機環境依序執行以下步驟：

1. 確認發行內容的 PR 已合併，切換至 `main` 並拉取最新代碼：
   ```powershell
   git checkout main
   git pull
   ```
2. 確認 `git status` 乾淨，無任何未提交變更。
3. 同步包含選用依賴的開發環境：
   ```powershell
   uv sync --extra garminconnect
   ```
4. 執行完整自動化測試：
   ```powershell
   uv run --with pytest pytest -q
   ```
5. 執行 Ruff 靜態檢查（規則集已在 `pyproject.toml` 鎖定，與 CI 一致）：
   ```powershell
   uv run --with ruff ruff check src tests --no-cache
   ```
6. 編譯 Windows EXE（PyInstaller 打包 CLI 與 UI，log 寫入 `.packaging-logs/`）：
   ```cmd
   scripts\build_exe.manual.cmd
   ```
7. 執行 EXE 冒煙測試：
   ```cmd
   scripts\smoke_exe.manual.cmd
   ```
   腳本會自動驗證：
   - CLI `--help` 與 `import-garminconnect --help`，並確認含 `--trackpoint-density`（用來擋下以舊原始碼打包的 EXE）。
   - CLI 預設輸出 `summary.txt`、`all_in_one.txt`、`runs\*.txt`，且未要求時不產生 `session_bundle`。
   - CLI `--write-coach-handoff` 仍產生舊版 `session_bundle.json / .md` 與 `coach_handoff.md`。
   - UI EXE 能啟動、開始監聽 port 並回應 HTTP 200，之後自動關閉。這一步由
     `scripts\smoke_ui_exe.ps1` 執行，瀏覽器可能會自動開一個分頁。
   若只想單獨測 UI EXE：
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_ui_exe.ps1
   ```

---

## 2. EXE 手動驗收 (Manual Validation)

冒煙測試通過後，建議再手動確認以下項目：

- [ ] **UI 啟動**：點兩下 `dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe`，主控台印出 `[INFO] Garmin TCX AI UI: http://localhost:PORT`，瀏覽器自動開啟。
- [ ] **Port 被佔用時仍可啟動**：再開第二個 UI EXE，應改用另一個 port 並正常開啟，而不是失敗。
- [ ] **本機模式**：選「本機 TCX 檔案 / 資料夾」並指定 `tests\fixtures`，按「開始產生 AI 文字檔」後成功顯示結果。
- [ ] **預設輸出位置**：EXE 版預設輸出在 `文件\GarminTCX-AI\processed\` 底下。
- [ ] **週表完整度**：`summary.txt` 的週跑量表有「完整度」欄，部分週標示「部分週（資料自 MM/DD 起）」或「部分週（截至 MM/DD）」。
- [ ] **all_in_one 結構**：依序為摘要、每次跑步總覽與每圈表，最後是「附錄：軌跡取樣」。
- [ ] **複製、下載與打開資料夾**：結果頁的複製按鈕、下載按鈕與「打開輸出資料夾」可正常運作。
- [ ] **不含 GPS**：開啟任一 `runs\*.txt`，確認沒有經緯度座標。
- [ ] **Garmin Connect 下載（選用）**：用真實帳號與「最近 14 天」下載，確認能產生文字檔，且部分週依選擇的日期範圍判斷。
- [ ] **Windows 認證管理員（選用）**：勾選儲存密碼並下載成功後，重開 EXE 可自動使用已儲存密碼，「刪除已儲存密碼」可移除。

---

## 3. Release Artifact 打包

### 3.1 產出兩個 zip

| 檔名 | 內容 | 對象 |
|---|---|---|
| `garmin-tcx-ai-v0.2.0-windows-ui.zip` | `garmin-tcx-ai-ui\`、README、LICENSE、NOTICE、RELEASE_NOTES | 大多數使用者 |
| `garmin-tcx-ai-v0.2.0-windows-onedir.zip` | `garmin-tcx-ai\`、`garmin-tcx-ai-ui\`、上述文件與本 checklist | 需要 CLI 的使用者 |

在專案根目錄的 PowerShell 執行：

```powershell
$v = "0.2.0"
New-Item -ItemType Directory -Force -Path release-artifacts | Out-Null

Compress-Archive -Force `
  -Path dist\garmin-tcx-ai-ui, README.md, LICENSE, NOTICE.md, RELEASE_NOTES.md `
  -DestinationPath "release-artifacts\garmin-tcx-ai-v$v-windows-ui.zip"

Compress-Archive -Force `
  -Path dist\garmin-tcx-ai, dist\garmin-tcx-ai-ui, README.md, LICENSE, NOTICE.md, RELEASE_NOTES.md, docs\10_final_release_checklist.md `
  -DestinationPath "release-artifacts\garmin-tcx-ai-v$v-windows-onedir.zip"
```

> [!WARNING]
> 不要改用 `tar.exe -a -C . README.md ...` 的寫法。v0.2.0 發行時該寫法在 PowerShell 下
> 會靜默漏掉 README、LICENSE 等根目錄文件，只留下警告訊息。MIT 授權要求散佈時附上 LICENSE。

### 3.2 上傳前驗證 zip

每個 zip 都必須通過以下檢查，才可以上傳：

```powershell
uv run python -c "import zipfile,sys; v=sys.argv[1]; [print(n, 'OK' if (z:=zipfile.ZipFile(f'release-artifacts/garmin-tcx-ai-v{v}-windows-{n}.zip')).testzip() is None and {'README.md','LICENSE','NOTICE.md','RELEASE_NOTES.md'} <= set(z.namelist()) and any(f.endswith('garmin-tcx-ai-ui.exe') for f in z.namelist()) else 'FAILED') for n in ('ui','onedir')]" $v
```

兩行都要顯示 `OK`。接著把 UI zip 解壓到一個全新的暫存資料夾，執行其中的
`garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe`，確認能開啟頁面，模擬下載者的實際使用情境。

### 3.3 嚴格安全限制

> [!IMPORTANT]
> - `release-artifacts/` 目錄與產生的 `*.zip` 檔案**絕對不可 commit** 至 Git 儲存庫。
> - `dist/`、`build/`、`.packaging-logs/`、`*.exe` 亦**絕對不可 commit**。
> - 打包前確認 `dist\` 內沒有 `*.tcx`、`*.fit`、`*.gpx`、`.env` 或任何個人資料：
>   ```powershell
>   Get-ChildItem dist -Recurse -Include *.tcx,*.fit,*.gpx,.env* | Select-Object FullName
>   ```
>   此指令應無輸出。

---

## 4. Git Tag

建議的 Tag 名稱：`v0.2.0`

### 4.1 建立時機

1. 發行內容的 PR 已合併至 `main`，且 `main` 上的 CI 通過。
2. 已在本機 `git checkout main` 並 `git pull`。
3. 已完成第 1 至 3 節，zip 驗證通過。

> [!WARNING]
> 如果該 tag 已經在遠端或本機存在，請勿強行覆蓋（`--force`），先停下來確認版本狀態。

### 4.2 建立指令

```powershell
git checkout main
git pull
git status
git tag -a v0.2.0 -m "Garmin TCX AI v0.2.0"
git push origin v0.2.0
```

---

## 5. GitHub Release

### 5.1 建立 Release

先把 Release 說明寫入一個本機暫存檔（不要放在 repo 內），再執行：

```powershell
$v = "0.2.0"
gh release create "v$v" --verify-tag --latest `
  --title "Garmin TCX AI v$v" `
  --notes-file <release-notes.md 的路徑> `
  "release-artifacts\garmin-tcx-ai-v$v-windows-ui.zip" `
  "release-artifacts\garmin-tcx-ai-v$v-windows-onedir.zip"
```

若上傳後才發現 zip 有誤，修正後用 `--clobber` 替換，不要刪除 Release 重建：

```powershell
gh release upload "v$v" --clobber "release-artifacts\garmin-tcx-ai-v$v-windows-ui.zip"
```

### 5.2 Release 說明應包含

- **下載哪一個**：UI zip 給大多數人，onedir zip 附 CLI。
- **使用步驟**：解壓縮 → 執行 `garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe` → 選資料來源 → 開始產生 → 複製 `all_in_one.txt` 給 AI。
- **保留整個資料夾**：只複製 `.exe` 出來會無法執行。
- **SmartScreen 提示**：EXE 未經程式碼簽章，首次執行會出現「Windows 已保護您的電腦」，需點「其他資訊」→「仍要執行」。
- **資料位置**：下載的 TCX 與輸出預設在 `文件\GarminTCX-AI\`。
- **本版變更摘要**：取自 `RELEASE_NOTES.md`。
- **限制**：Garmin Connect 下載使用非官方介面，可能因 Garmin 變更而暫時失效；本機 TCX 模式不受影響。僅支援 Windows。不提供訓練建議或醫療解讀。
- **授權**：MIT License，Copyright (c) 2026 Jia-Long Chen。

### 5.3 發行後確認

- [ ] Release 標示為 Latest，非 Draft、非 Pre-release。
- [ ] 兩個 zip 的遠端大小與本機檔案大小一致（兩邊的數字要完全相同）：
  ```powershell
  gh release view v0.2.0 --json assets -q '.assets[] | .name, .size'
  Get-ChildItem release-artifacts\garmin-tcx-ai-v0.2.0-*.zip | Select-Object Name, Length
  ```
- [ ] 從 Release 頁面實際下載 UI zip，解壓後可執行。
