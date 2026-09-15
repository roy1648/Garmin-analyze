# Garmin TCX AI

把 Garmin Connect 的跑步記錄一口氣抓下來，轉成 AI（ChatGPT 等）好讀的
純文字檔，讓你不用再一筆一筆手動下載。全程在本機執行，不上傳任何資料。

## 你會得到什麼

執行一次之後，輸出資料夾長這樣：

```text
<output>/
  summary.txt        # 精煉報告：期間總計、週跑量（週一到週日，標示完整週/部分週）、每日、每次跑步一行
  all_in_one.txt     # summary → 每次跑步的總覽與每圈表 → 附錄：軌跡取樣。整份餵給 AI 最方便
  runs/
    2026-07-02_1958_7.18km.txt   # 每次跑步一份：總覽、每圈 (Lap) 表、軌跡取樣
    2026-07-05_2143_6.02km.txt
```

- 每次跑步的檔案包含距離、時間、配速、心率、步頻、功率、高度、每圈表格，
  以及依圈長自動取樣的軌跡表（短圈／間歇每 5 秒一列，長圈每 30 秒一列），
  所以間歇訓練的結構會保留下來，檔案又不會太大（一次 7 km 約 20 KB）。
- 週表有「完整度」欄：資料範圍沒有涵蓋整週時標示「部分週（資料自 MM/DD 起）」或
  「部分週（截至 MM/DD）」，避免把部分週跑量拿去和完整週比較。Garmin Connect
  下載模式會用你選的日期範圍判斷；本機模式則用跑步日期的頭尾。
- `all_in_one.txt` 把軌跡取樣集中放在最後的附錄，日常排課只需讀前面的摘要、
  每次跑步總覽與每圈表；要細查某次心率或掉速時再往下看附錄。
- 所有 txt 都不含 GPS 座標。步頻是 Garmin 原始值，未做 x2 換算。
- 舊版的 `session_bundle.json / .md` 與 `coach_handoff.md` 仍可用，
  但預設不再產生。

## 專案結構

```text
src/garmin_tcx_ai/      # Python 核心套件 (Parser, Normalizer, ai_text, Pipeline, CLI, UI)
scripts/                # Windows 啟動、驗證與打包腳本
tests/                  # pytest 測試套件
tests/fixtures/         # 已提交的最小清理測試資料 (Sanitized Fixtures)
data/raw/               # 下載的原始 TCX (Git 忽略)
data/processed/         # 本機轉換輸出目錄 (Git 忽略)
```

打包成 EXE 後，下載與輸出改放在 `文件\GarminTCX-AI\`，換電腦也一樣。

## 快速開始 (Quick Start)

```powershell
uv sync
uv run --with pytest pytest -q
uv run --with ruff ruff check src tests --no-cache
```

## 本機 UI（建議用法）

```powershell
uv run python -m garmin_tcx_ai.ui_exe_launcher
```

或在 Windows 直接雙擊 `scripts\run_ui.cmd`。啟動器會自動挑一個空閒的
port（8501 可用時優先），把網址印在視窗裡，並在伺服器就緒後自動開啟瀏覽器。

若要使用 Garmin Connect 下載，請先安裝 optional dependency：

```powershell
uv sync --extra garminconnect
uv run --extra garminconnect python -m garmin_tcx_ai.ui_exe_launcher
```

### UI 操作流程

1. **資料來源**：選「Garmin Connect 下載」（輸入帳號、密碼、日期範圍，
   有「最近 7 / 14 / 28 / 90 天」快速按鈕）或「本機 TCX 檔案 / 資料夾」。
2. **輸出位置**：預設自動建立一個帶時間戳的資料夾，也可自行選擇。
3. **開始產生 AI 文字檔**：完成後可直接預覽、複製或下載 `all_in_one.txt`
   與 `summary.txt`，或打開輸出資料夾。

密碼可勾選存到 Windows 認證管理員，只在登入成功後才儲存，不會寫進任何專案檔案。

進階設定（通常不用改）：軌跡取樣密度、時區、活動類型、下載資料夾、
是否額外產生舊版輸出、舊版輸出的 GPS 政策。

## CLI

```powershell
# 本機 TCX 檔案或資料夾 → txt
uv run garmin-tcx-ai bundle --input data/raw/garminconnect --output data/processed/run1

# Garmin Connect 下載 + 轉換
uv run --extra garminconnect garmin-tcx-ai import-garminconnect `
  --start-date 2026-07-01 `
  --end-date 2026-07-14 `
  --download-dir data/raw/garminconnect `
  --output data/processed/garminconnect
```

### 主要參數

- `--input`：單一 `.tcx` 或包含 `.tcx` 的資料夾（只掃第一層）。
- `--output`：輸出資料夾。
- `--trackpoint-density {compact,standard,detailed}`：軌跡取樣密度，預設 `standard`。
- `--timezone`：本地時間時區，預設 `Asia/Taipei`。
- `--no-ai-text`：不產生 txt。
- `--write-session-bundle`：額外產生舊版 `session_bundle.json / .md`。
- `--write-coach-handoff`：額外產生 `coach_handoff.md`（會一併產生 session bundle）。
- `--write-atomic`：額外產生每筆活動的除錯檔（`activity.json`、`trackpoints.csv` …）。
- `--gps-policy`、`--max-gap-minutes`：只影響舊版輸出與除錯檔。

`import-garminconnect` 另有 `--start-date`、`--end-date`、`--activity-type`、
`--download-dir`、`--email`、`--limit`、`--overwrite`。CLI 不接受密碼參數，
會以互動式 `getpass` 輸入。

## 開發與測試

```powershell
uv run python -m pytest -q
uv run python -m ruff check src tests --no-cache
```

用已提交的測試資料做 smoke：

```powershell
uv run garmin-tcx-ai bundle --input tests/fixtures --output data/processed/cli_fixture_smoke
```

## Windows EXE

以 PyInstaller 打包成資料夾式（onedir）EXE：

```cmd
scripts\build_exe.manual.cmd
scripts\smoke_exe.manual.cmd
```

產出 `dist\garmin-tcx-ai\garmin-tcx-ai.exe`（CLI）與
`dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe`（UI）。把整個
`dist\garmin-tcx-ai-ui\` 資料夾複製到另一台電腦即可直接執行，不需安裝 Python。
詳見 [docs/09_windows_exe_packaging.md](docs/09_windows_exe_packaging.md)。

## 資料安全

- 不 commit 原始 TCX、`.env`、token、`data/raw/`、`data/processed/`。
- txt 輸出不含 GPS 座標；心率、功率等仍屬個人資料，分享給 AI 前請自行確認。
- Garmin 密碼只存在 Windows 認證管理員，不寫入任何檔案或 log。

## Release & License

- **版本**：v0.2.0（見 [RELEASE_NOTES.md](RELEASE_NOTES.md)）
- **Author**：Jia-Long Chen ・ **GitHub**：roy1648 ・ **License**：MIT
- 更多文件：[docs/07_user_manual.md](docs/07_user_manual.md)、
  [docs/07_known_limitations.md](docs/07_known_limitations.md)、
  [docs/10_final_release_checklist.md](docs/10_final_release_checklist.md)
