# Garmin TCX AI

個人 Garmin Connect 資料 ETL 與分析專案。

本專案提供一個將 Garmin 手動匯出的 Running TCX 檔案進行解析、
資料清理、隱私遮蔽，並輸出為 AI 教練或工具可讀的 Session Bundle。

## 專案結構

```text
src/garmin_tcx_ai/      # Python 核心套件 (Parser, Normalizer, Exporters, Pipeline, CLI)
scripts/convert_tcx.py  # 歷史腳本範例（不建議使用，請改用 garmin-tcx-ai CLI 或 Streamlit UI）
tests/                  # pytest 測試套件
tests/fixtures/         # 已提交的最小清理測試資料 (Sanitized Fixtures)
data/samples/           # 本機測試資料目錄 (Git 忽略)
data/processed/         # 本機轉換輸出目錄 (Git 忽略)
```

## 快速開始 (Quick Start)

```powershell
uv sync
uv run --with pytest pytest -q
uv run --with ruff ruff check src tests --no-cache
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

## 本機 UI 介面 (Local UI Usage)

啟動 (預設本機模式，無 Garmin Connect 下載功能)：

```powershell
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

啟動 (含 Garmin Connect 下載與憑證儲存功能，需要安裝 optional dependency)：

```powershell
uv sync --extra garminconnect
uv run --extra garminconnect streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

### 使用與功能說明

* **資料來源選擇 (Data Source Selection)**：可在最上方切換：
  - **本機 TCX 檔案 / 資料夾**：維持標準本機檔案處理。
  - **Garmin Connect 下載**：輸入 Email、密碼與日期範圍，即可自動下載並分析活動。
* **密碼安全儲存 (Keyring Credential Storage)**：
  - 在 Windows 上，若勾選「將密碼儲存到 Windows Credential Manager」，密碼會以安全性機制儲存於 Windows 11 的 Credential Manager 中。
  - 勾選「使用已儲存密碼」，會在 Email 輸入後自動帶入已儲存密碼。
  - 提供「刪除已儲存 Garmin 密碼」按鈕，可一鍵移除已儲存的金鑰。
  - 密碼絕不寫入專案內任何設定檔、`.env` 或 logs。
* **手動輸入路徑 (Manual input path)**：可手動在「Input path」欄位輸入單一 TCX 檔案或資料夾路徑。
* **原生選取器按鈕 (Native picker buttons)**：可使用「選擇 TCX 檔案」或「選擇 TCX 資料夾」按鈕，透過本機 OS 視窗選取路徑。
* **輸出資料夾選取 (Output folder selection)**：可透過「選擇輸出資料夾」按鈕選擇目錄，或使用「重新產生預設輸出資料夾」產生具備唯一 timestamp 的輸出路徑。
* **進階設定 (Advanced settings)**：可展開「進階設定」調整 GPS Policy、時區 (Timezone)、Session 分組間隔門檻，以及是否輸出詳細除錯檔案 (Atomic Artifacts)。
* **打開輸出資料夾按鈕 (Output folder open button)**：轉換成功後可點擊「打開輸出資料夾」按鈕，嘗試透過本機檔案總管開啟輸出目錄。
* **複製與手動複製功能 (Copy/manual-copy)**：可直接點選「複製」按鈕複製產生的輸出內容全文，若瀏覽器權限限制，亦可透過「手動複製」展開區的純文字框進行複製。支援以下檔案：
  - `session_bundle.json`
  - `session_bundle.md`
  - `coach_handoff.md`
* **滿版預覽**：頁面下方以滿版寬度且完整長度顯示產生的三個輸出檔案內容。

## Garmin Connect TCX Importer (Local Optional)

這是 post-MVP 的 local-only optional importer。它只負責登入 Garmin
Connect、把指定日期區間的 activities 下載成 TCX 到本機資料夾，然後交給既有
`garmin-tcx-ai bundle` pipeline 產生相同的 `session_bundle` /
`coach_handoff`。它不改變 session bundle contract，也不新增雲端同步、背景排程、
資料庫、官方 Garmin Developer API、AI API upload 或 AI coaching。

安裝 optional dependency：

```powershell
uv sync --extra garminconnect
```

使用範例：

```powershell
uv run --extra garminconnect garmin-tcx-ai import-garminconnect `
  --start-date 2026-07-01 `
  --end-date 2026-07-08 `
  --activity-type running `
  --download-dir data/raw/garminconnect `
  --output data/processed/garminconnect `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --max-gap-minutes 30 `
  --write-coach-handoff
```

若本機 `uv run --extra garminconnect` 因環境或 lock 狀態無法使用，可改用：

```powershell
uv run --with garminconnect --with curl_cffi garmin-tcx-ai import-garminconnect `
  --start-date 2026-07-01 `
  --end-date 2026-07-08 `
  --activity-type running `
  --download-dir data/raw/garminconnect `
  --output data/processed/garminconnect `
  --gps-policy redact_start_end `
  --timezone Asia/Taipei `
  --max-gap-minutes 30 `
  --write-coach-handoff
```

安全邊界：

- CLI 只接受 `--email`，不接受 password 參數；password 會用互動式
  `getpass` 輸入。
- Garmin token、credentials、`.env`、`~/.garminconnect` 與任何私人活動資料
  不可 commit。
- 下載的 TCX 會落在 `data/raw/` 底下，該路徑已由 `.gitignore` 忽略。
- Garmin Connect importer 是 optional CLI 與 UI feature；在 UI 模式中，支援藉由系統金鑰庫 (Windows Credential Manager) 安全儲存密碼。Windows EXE packaging kit 已支援將 Garmin Connect 相關 optional dependencies (包含登入與密碼管理機制) 打包進 EXE 檔。

## Windows Local Launcher

For Windows local usage, start the UI with:

```cmd
scripts\run_ui.cmd
```

This script:

* checks that `uv` is available
* runs `uv sync`
* starts the Streamlit Local UI
* does not use system Python directly
* does not create an EXE

For validation:

```cmd
scripts\run_validation.cmd
scripts\run_cli_smoke.cmd
```

EXE packaging is supported via a manual local compilation kit. See:
- [docs/09_windows_exe_packaging.md](file:///d:/01-Git%20code/10-garmin%20project/docs/09_windows_exe_packaging.md)

Manual build, smoke test, and cleanup scripts are located at:
- `scripts\build_exe.manual.cmd`
- `scripts\smoke_exe.manual.cmd`
- `scripts\clean_packaging_artifacts.cmd`

## Release, Packaging & License

- **Current local release version**: v0.1.0
- **Author**: Jia-Long Chen
- **GitHub**: roy1648
- **License**: MIT
- **Copyright**: Copyright (c) 2026 Jia-Long Chen
- **Windows EXE Distribution**: Packaged as a folder-based (`onedir`) ZIP artifact.
- **Local Compilation**:
  - Build locally with `scripts\build_exe.manual.cmd`
  - Smoke test with `scripts\smoke_exe.manual.cmd`
- **Data Safety**:
  - Real Garmin login and credential validation are manual and local-only.
  - Do NOT commit generated binaries (`dist/`, `build/`, `release-artifacts/`, `*.exe`, `*.zip`) or private Garmin data (`data/raw/`, `data/processed/`, `*.tcx`).

For the complete final release steps, manual validation guidelines, and packaging details, please refer to:
- [docs/10_final_release_checklist.md](file:///d:/01-Git%20code/10-garmin%20project/docs/10_final_release_checklist.md)
- [docs/06_release_candidate_validation.md](file:///d:/01-Git%20code/10-garmin%20project/docs/06_release_candidate_validation.md)
- [docs/07_known_limitations.md](file:///d:/01-Git%20code/10-garmin%20project/docs/07_known_limitations.md)
- [docs/09_windows_exe_packaging.md](file:///d:/01-Git%20code/10-garmin%20project/docs/09_windows_exe_packaging.md)
