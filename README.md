# Garmin TCX AI

個人 Garmin Connect 資料 ETL 與分析專案。

本專案提供一個將 Garmin 手動匯出的 Running TCX 檔案進行解析、
資料清理、隱私遮蔽，並輸出為 AI 教練或工具可讀的 Session Bundle。

## 專案結構

```text
src/garmin_tcx_ai/      # Python 核心套件 (Parser, Normalizer, Exporters, Pipeline, CLI)
scripts/convert_tcx.py  # 腳本範例入口
tests/                  # pytest 測試套件
tests/fixtures/         # 已提交的最小清理測試資料 (Sanitized Fixtures)
data/samples/           # 本機測試資料目錄 (Git 忽略)
data/processed/         # 本機轉換輸出目錄 (Git 忽略)
```

## 安裝與執行

本專案支援 Python 3.12+，並建議使用 `uv` 進行環境管理。

若要直接以 CLI 轉換 TCX 檔案：

```powershell
# 轉換單一檔案或資料夾至指定的 session bundle
uv run garmin-tcx-ai bundle `
  --input data/samples `
  --output data/processed/smoke_local `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --max-gap-minutes 30 `
  --write-coach-handoff
```

### CLI 參數說明

- `--input`：必填。可以指定單一 `.tcx` 檔案，或是包含 `.tcx` 檔案的資料夾。如果是資料夾，僅會掃描第一層檔案。
- `--output`：必填。指定輸出的目標資料夾。
- `--gps-policy`：GPS 隱私政策，預設為 `redact_start_end`（模糊化起終點）。可選 `keep` 或 `remove`。
- `--timezone`：本地時間轉換時區，預設為 `Asia/Taipei`。
- `--max-gap-minutes`：session candidate 分組的活動間隔門檻（分鐘），預設為 `30`。
- `--write-atomic`：若加上此旗標，會額外輸出 per-activity 的除錯用詳細 artifacts (`activity.json`、`trackpoints.csv`、`ai_summary.json/md`)。
- `--write-coach-handoff`：若加上此旗標，會額外在 `session_bundle` 目錄下產生 `coach_handoff.md`，內含 manual context 空白欄位及 session bundle 主要內容，可直接複製提供給跑步教練 Agent。

## 開發與測試

執行 pytest 測試：

```powershell
uv run python -m pytest -q
```

執行 Ruff 靜態檢查：

```powershell
uv run python -m ruff check src tests --no-cache
```

## 本機 Smoke 測試

使用已提交的測試資料 (Sanitized Fixtures) 驗證 CLI：

```powershell
uv run garmin-tcx-ai bundle `
  --input tests/fixtures `
  --output data/processed/cli_fixture_smoke `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --max-gap-minutes 30 `
  --write-coach-handoff
```

## 本機 UI 介面

啟動：

```powershell
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

使用流程：

1. 在 Input path 欄位，可直接輸入路徑，或點擊旁邊的「選擇檔案」/「選擇資料夾」按鈕，透過本機檔案選取器選擇輸入來源。
2. UI 會先檢查路徑是否存在，以及可偵測到幾個 TCX 檔案。
3. 確認或重新產生 output folder。您也可以點擊「選擇資料夾」按鈕以選取特定的輸出目錄。
4. 一般情況只需要保留預設參數。
5. 需要時再展開「進階設定」調整 GPS policy、timezone、max gap minutes 或 atomic artifacts。
6. 按下「開始轉換」。
7. 轉換成功後，可在頁面最下方以完整寬度預覽 `session_bundle.md` 與 `coach_handoff.md`。

輸出結果操作：
- 可複製 `session_bundle.json` 全文。
- 可複製 `session_bundle.md` 全文。
- 可複製 `coach_handoff.md` 全文。
- 可嘗試從 UI 打開輸出資料夾。
- 若系統不允許自動打開資料夾，仍可複製頁面顯示的 output folder 路徑手動開啟。

提示：
- UI 僅在本機執行。
- 不會上傳 Garmin 資料。
- 輸出仍遵守既有 session bundle contract。
- CLI 仍可繼續使用。



