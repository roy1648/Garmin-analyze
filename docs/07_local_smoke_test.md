# 本機 Smoke Test 指引

本文件說明如何利用 `garmin-tcx-ai` CLI 進行本機端功能驗證（Smoke Test）。

## 1. 準備工作

進行測試前，請確認您的虛擬環境運作正常。您可以透過以下指令重新打包安裝套件：

```powershell
uv pip install -e .
```

## 2. 執行 Fixture Smoke 測試

使用已提交的測試資料（Sanitized Fixtures）來驗證 CLI 的協調與輸出功能。

執行以下指令：

```powershell
uv run garmin-tcx-ai bundle `
  --input tests/fixtures `
  --output data/processed/cli_fixture_smoke `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --max-gap-minutes 30
```

### 預期終端機輸出

```text
Warning: Unsupported activity in 'cycling_activity.tcx': Activity sport 'Biking' is not supported for MVP. Only Running is supported.
Warning parsing TCX in 'invalid.tcx': Invalid XML in 'invalid.tcx': no element found: line 9, column 0
Successfully processed 2 activities.
Output folder: <專案路徑>/data/processed/cli_fixture_smoke
```

## 3. 驗證產出結構

轉換完成後，請檢查產出的資料夾結構：

- **基本輸出**：只產生 `session_bundle` 目錄與對應檔案。
  ```text
  data/processed/cli_fixture_smoke/session_bundle/session_bundle.json
  data/processed/cli_fixture_smoke/session_bundle/session_bundle.md
  ```
- **詳細輸出**：若指令加上 `--write-atomic` 參數，則會額外輸出每個活動的 debug 檔案（例如 `activity.json`、`trackpoints.csv` 等）。

## 4. 資料安全警示

> [!CAUTION]
> - 輸出的 `data/processed/` 資料夾已被列入 `.gitignore`。
> - **切勿**將個人真實的活動檔案（位於 `data/raw/` 或 `data/processed/`）提交至 Git 中。
