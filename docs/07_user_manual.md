# 使用者操作手冊

更新日期：2026-07-07

## 目前專案狀態

本專案目前是個人 Garmin Connect TCX ETL 與分析工具，包含以下核心模組：

- `parser`：解析手動匯出的 Garmin Running TCX fixture。
- `normalizer`：套用 normalized activity 結構與 GPS policy。
- `privacy`：支援 `keep`、`remove`、`redact_start_end` GPS policy。
- `summary`：產生 factual AI summary，不輸出 coaching 或 medical advice。
- `session`：建立 multi-TCX session bundle candidate。
- `exporters`：輸出 `activity.json`、`trackpoints.csv`、
  `ai_summary.json`、`ai_summary.md`、`session_bundle` artifacts。
- `ui_streamlit`：本機 Streamlit UI 介面，是已批准的 post-MVP local usability layer，提供友善的操作介面。
- `cli`：提供 `garmin-tcx-ai` 命列行介面以供批次與腳本整合使用。

重要限制：

- MVP 範圍限於手動匯出的 Garmin Connect Running TCX。
- 目前不包含 Garmin API login、GarminDB、database、cloud-based Web UI、cloud sync
  或 AI API upload。
- 測試使用 `tests/fixtures/` 內的 sanitized TCX fixtures，不應使用私人
  Garmin 原始資料。

## 資料安全

請把 Garmin 密碼、token、`.env`、原始 TCX、處理後輸出與任何含 GPS 或
健康指標的私人資料留在 Git 之外。

建議路徑：

- committed sanitized fixtures：`tests/fixtures/`
- 本機私人 sample：`data/samples/`
- 原始私人資料：`data/raw/`
- 產生的私人輸出：`data/processed/`

`data/raw/` 與 `data/processed/` 不應 commit。GPS coordinates、heart rate、
power、cadence 與健康資料都應視為敏感資料；分享給任何 AI 或外部服務前，
請先人工檢查輸出內容。

## uv 虛擬環境用法

專案有 `uv.lock`，建議以 uv 執行測試與工具。乾淨環境下，因為
`pyproject.toml` 尚未宣告 `pytest` 與 `ruff` 為 project dependencies，
可用 `--with` 臨時帶入測試工具，不必修改專案設定。

一般 PowerShell 用法：

```powershell
uv run --with pytest python -m pytest -q
uv run --with ruff python -m ruff check src tests --no-cache
```

若 Windows 權限導致 uv cache 或 pytest temp 目錄失敗，可改用可寫的本機
暫存位置：

```powershell
$env:UV_CACHE_DIR = Join-Path $env:TEMP 'garmin-uv-cache'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP 'garmin-uv-venv'
uv run --with pytest python -m pytest -q --basetemp .pytest-tmp
```

若 pytest 嘗試寫入 `.pytest_cache` 時出現 `WinError 5` warning，可加上
`-p no:cacheprovider`：

```powershell
$env:UV_CACHE_DIR = Join-Path $env:TEMP 'garmin-uv-cache'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP 'garmin-uv-venv'
uv run --with pytest python -m pytest -q --basetemp .pytest-tmp -p no:cacheprovider
```

如果要明確使用 Python 3.12，可在本機已安裝 Python 3.12 時指定：

```powershell
uv run --python 3.12 --with pytest python -m pytest -q --basetemp .pytest-tmp
```

## 如何測試目前 code

建議先執行完整 pytest：

```powershell
uv run --with pytest python -m pytest -q --basetemp .pytest-tmp -p no:cacheprovider
```

再執行 Ruff：

```powershell
uv run --with ruff python -m ruff check src tests --no-cache
```

目前已驗證結果：

- `uv run --with pytest python -m pytest -q --basetemp .pytest-tmp -p no:cacheprovider`
  通過，測試通過數量以 PR / CI 結果為準。
- `uv run --with ruff python -m ruff check src tests --no-cache` 通過，結果為
  `All checks passed!`。

如果直接執行：

```powershell
uv run python -m pytest -q
uv run python -m ruff check src tests --no-cache
```

乾淨 uv 環境可能會失敗並顯示 `No module named pytest` 或
`No module named ruff`。這代表測試工具尚未宣告為 project dependency，
不代表 application code 測試失敗。

## 執行與使用方式

本專案提供 CLI 工具與 Streamlit 本機 UI 作為主要的操作與執行入口（Local UI 作為已批准的 post-MVP local usability layer）。

### 1. CLI 工具使用方式

使用 `garmin-tcx-ai` 命令執行轉換：

```powershell
# 範例：將 tests/fixtures 中的 TCX 檔案轉換為 session bundle
uv run garmin-tcx-ai bundle --input tests/fixtures --output data/processed/smoke_cli --write-coach-handoff
```

### 2. Streamlit 本機 UI 使用方式

執行以下指令啟動本機網頁操作介面：

```powershell
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

## 模組層級操作範例

現階段如需手動 smoke test，可在 Python 中直接呼叫 package API，並只使用
sanitized fixture 或本機 ignored sample。

```powershell
uv run --with pytest python
```

Python REPL 範例：

```python
from pathlib import Path

from garmin_tcx_ai.exporters import (
    write_activity_json,
    write_ai_summary_json,
    write_ai_summary_markdown,
    write_session_bundle_json,
    write_session_bundle_markdown,
    write_trackpoints_csv,
)
from garmin_tcx_ai.normalizer import normalize_activity
from garmin_tcx_ai.parser import parse_tcx

activity = parse_tcx(Path("tests/fixtures/minimal_running.tcx"))
normalized = normalize_activity(activity, "redact_start_end")
output_dir = Path("data/processed/manual_smoke")

write_activity_json(normalized, output_dir)
write_trackpoints_csv(normalized, output_dir)
write_ai_summary_json(normalized, output_dir)
write_ai_summary_markdown(normalized, output_dir)
write_session_bundle_json([normalized], output_dir)
write_session_bundle_markdown([normalized], output_dir)
```

輸出資料夾會包含 per-activity artifacts 與 `session_bundle/`。若改用私人
TCX，請確認輸出路徑位於 Git ignored 區域，並在分享前檢查 GPS policy。

## 目前適合檢查的輸出

單一 activity exporter 會產生：

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

Session bundle exporter 會產生：

- `session_bundle/session_bundle.json`
- `session_bundle/session_bundle.md`

Markdown summary 與 session bundle 應維持 factual output，不包含 GPS
coordinates、route details、coaching advice、medical interpretation 或
workout role inference。
