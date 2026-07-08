# 任務拆解

本文件描述 MVP 的漸進式開發階段。每個 PR 應維持單一 objective，避免
scope creep。

## Phase 1：專案骨架（已完成）

目標：

- 建立 Python package、測試結構與基本文件。

完成條件：

- `src/garmin_tcx_ai/` 存在。
- tests 可執行。
- README / docs 說明 MVP 範圍。

## Phase 2：Fixture 與資料安全（已完成）

目標：

- 建立 minimal sanitized TCX fixture。
- 確認 private Garmin data 不進 Git。

完成條件：

- `tests/fixtures/` 使用 sanitized fixture。
- `data/raw/`、`data/processed/`、`data/samples/` 不 commit。

## Phase 3：Models（已完成）

目標：

- 建立 activity、lap、trackpoint、privacy、warning dataclass models。

完成條件：

- 缺漏欄位可用 `None` 表示。
- Public functions / models 有 type hints。
- Data contract 記錄 models 邊界。

## Phase 4：TCX Parser（已完成）

目標：

- 解析 Running TCX 的 activity、lap、trackpoint。
- 讀取 Garmin extension 欄位，例如 Speed、RunCadence、Watts。

完成條件：

- 支援 multi-lap。
- Malformed XML 與 unsupported sport 有明確錯誤。
- Parser 不做 privacy 或 role inference。

## Phase 5：Normalizer 與 GPS Privacy（已完成）

目標：

- 將 parser output normalize 成 `ParsedActivity`。
- 套用 GPS policy。

完成條件：

- `keep`、`remove`、`redact_start_end` 可測。
- 缺漏欄位保留 `None`。
- 不修改 raw TCX input。

## Phase 6：JSON Exporter（已完成）

目標：

- 輸出 `activity.json`。

完成條件：

- JSON top-level keys 完整。
- `None` 輸出為 `null`。
- Datetime 輸出 ISO 8601。
- 使用 safe activity folder。

## Phase 7：CSV Exporter（已完成）

目標：

- 輸出 `trackpoints.csv`。

完成條件：

- CSV 欄位順序符合 data contract。
- 缺漏值為空白 cell。
- GPS 欄位符合 privacy policy。

## Phase 8：單一 Activity AI Summary（已完成）

目標：

- 輸出 per-activity `ai_summary.json` 與 `ai_summary.md`。

完成條件：

- Activity、lap、split、elevation、data quality、privacy、data policy
  欄位完整。
- 不包含 GPS 座標或 route details。
- 不包含 role inference、coaching advice 或 medical interpretation。

## Phase 9：Multi-TCX Session Bundle + No-Inference Policy（PR #9）

目標：

- 建立 coach-facing `session_bundle.json` / `session_bundle.md`。
- 單一 TCX 與多個 TCX 都統一輸出 session bundle。
- 移除 summary output 的 Suggested AI Analysis Questions 與 trend
  semantic labels。
- 補強 factual fields，讓 AI 工具可讀取但不能推論。

允許修改檔案：

- `src/garmin_tcx_ai/session.py`
- `src/garmin_tcx_ai/summary.py`
- `src/garmin_tcx_ai/exporters.py`
- `src/garmin_tcx_ai/__init__.py`
- `tests/test_session.py`
- `tests/test_summary.py`
- `tests/test_exporters.py`
- `docs/02_data_contract.md`
- `docs/03_acceptance_tests.md`
- `docs/04_architecture.md`
- `docs/05_task_breakdown.md`

完成條件：

- `build_session_bundle()` 支援一個或多個 normalized activities。
- Session grouping 使用 configured timezone 的 local date、same sport、
  start-time gap。
- Grouping 明確標示為 candidate，不視為 TCX 來源事實。
- 每個 activity 保留單一 TCX identity。
- Activity / lap role 為 `null`，`role_source == "not_inferred"`。
- `manual_context` 欄位為 manual-only placeholders，不從 TCX 推論。
- Lap summary 包含 `pace_reliability` 與 `reliability_reason`。
- Activity / lap / session level 包含 raw cadence 與 power factual metrics。
- Cadence 不做 x2 conversion，`avg_cadence_spm` 與 `conversion_rule`
  為 `null`。
- Activity / session 包含 `start_time_local`、`timezone`、`local_date`。
- Invalid `timezone_name` raise `ValueError`。
- `computed_split_metrics` 保留固定公式 policy，不輸出
  faster/slower/stable。
- `interpretation_level` 為
  `limited_for_interval_or_mixed_lap_activity`。
- Markdown 不包含 GPS 座標、route details、coaching advice、medical
  interpretation 或 Suggested AI Analysis Questions。
- `write_session_bundle_json()` 與 `write_session_bundle_markdown()` 輸出到
  固定 `session_bundle/` 目錄。
- Docs 說明 coach-facing standard output 是 session bundle；
  per-activity artifacts 是 atomic/debug/audit artifacts。
- pytest 與 Ruff 使用 uv 驗證通過。

非目標：

- CLI 或 batch CLI command。
- Garmin Connect login。
- Garmin API。
- GarminDB。
- Database / SQLite。
- Web UI。
- OpenAI / Claude / Gemini / NotebookLM API。
- AI service upload。
- Planned workout matching。
- Manual feedback input。
- Weekly summary。
- HR zone / time in zone。
- AI coaching、training interpretation 或 role inference。

## Phase 10：Report wording hardening / local smoke documentation

目標：

- 持續讓 `docs/03_acceptance_tests.md` 對應 pytest cases。
- 強化 report wording，避免暗示多個 TCX 被合併成一堂訓練。

完成條件：

- Tests 不依賴 private local samples。
- Report wording avoids implying that multiple TCX files are merged into one
  workout.
- Real-data smoke test 只使用 local ignored path。
- Smoke output 不 commit。

## Phase 11：Minimal Session Bundle CLI (PR #11)

目標：

- 建立一個最小可用 CLI，可用一條指令把本機 Garmin TCX 檔案轉成 AI 教練可讀的 session bundle。

完成條件：

- 支援 `garmin-tcx-ai` 入口命令與 `bundle` 子命令。
- 使用 `argparse`，無額外 CLI 套件依賴。
- 支援單一 TCX 與目錄的輸入偵測（第一層 `.tcx`，非遞迴）。
- 支援自訂與預設的時區、合併時間差、GPS 隱私政策。
- 預設僅輸出 `session_bundle` 檔案，支援 `--write-atomic` 參數寫出詳細 per-activity 除錯檔案。
- 包含完整錯誤捕捉與 exit code 回傳。
- 完成 CLI pytest 測試覆蓋。
- 排除 Suggested Questions 與 role inference 等推論內容。

## Phase 12：Coach Handoff Markdown (PR #12)

目標：

- 新增可選的 `--write-coach-handoff` CLI 旗標。
- 產生 `session_bundle/coach_handoff.md` 作為直接複製給跑步教練 Agent 的 Markdown 報告。

完成條件：

- 僅在傳入旗標時輸出 `session_bundle/coach_handoff.md`。
- Handoff 報告包含 manual context 空白欄位以供手動填寫。
- Handoff 報告不包含 GPS 座標與 route details。
- Handoff 報告不包含 Suggested Questions 與 AI coaching advice。
- Handoff 報告包含 `session_bundle.md` 的所有核心內容。
- 單元測試與 CLI 測試覆蓋 handoff 的生成與內容安全性。

## Phase 13：Traditional Chinese Markdown wording polish (PR #13)

目標：

- 將 coach-facing Markdown 輸出（`session_bundle.md`、`coach_handoff.md` 等）翻譯與優化為台灣繁體中文，保留核心專有名詞，提升易讀性。

完成條件：

- 輸出 Markdown 標題、說明字句與部分狀態轉換為台灣繁中。
- 保留關鍵英文術語（如 Data Policy, Export Scope, Session Candidates, Laps 等）作為雙語對照。
- 單元測試與 CLI 測試覆蓋繁中字句，確認不包含舊版誤導詞彙。

## Phase 14：MVP Contract Hardening & Closure (PR #14)

目標：

- 修正 `session_bundle.md` 中的 Data Policy 契約穩定性，還原 4 個核心英文契約句以供下游消費端或自動化測試進行精確斷言。
- 補齊對應的單元測試與文件收斂，宣布 MVP 完成。

完成條件：

- `render_session_bundle_markdown()` 的 Markdown 輸出中，Data Policy 段落及報告首部完整包含指定的 4 個英文契約句。
- pytest 單元測試能成功斷言這 4 個英文契約句的存在。
- 文件與 README 完成收斂與整理。
- **MVP 收斂公告**：本專案已正式進入關閉與收斂模式 (closure mode)。未來所有 PR 均不得新增支線或主要功能（例如：HR zone、Garmin zone、AI coaching、課表角色推論、週報、UI、資料庫、Garmin API、NotebookLM、OpenAI/Claude/Gemini API），除非使用者明確改變專案範疇並批准。

## Phase 15：Shared Pipeline Use Case for CLI and UI

目標：
- 將 CLI 的核心 bundle 執行流程抽出成 `pipeline.run_bundle()`。
- CLI 與未來 UI 共用同一個 execution path。
- 保留 CLI 既有行為與輸出契約。

完成條件：
- 新增 `BundleRunConfig` 與 `BundleRunResult`。
- CLI 改為呼叫 shared pipeline。
- 既有 CLI tests 全部通過。
- 新增 pipeline unit tests。
- 不新增 UI、不新增依賴、不修改 parser/normalizer/exporter/session contract。


## Phase 16：Minimal Streamlit Local UI (post-MVP Local UI usability phase)

目標：
- 新增本機 Streamlit UI，降低日常操作門檻。
- UI 呼叫 PR #15 抽出的 shared pipeline use case。
- 保留 CLI 作為自動化與工程入口。

完成條件：
- 新增 `ui_streamlit.py`。
- UI 可輸入 TCX 檔案或資料夾路徑。
- UI 可設定 GPS policy、timezone、max gap minutes、coach handoff 與 atomic artifacts。
- UI 可呼叫 `run_bundle()` 執行轉換。
- UI 可顯示 success / error / warnings / output paths。
- UI 可預覽 `session_bundle.md` 與 `coach_handoff.md`。
- 新增不依賴 Streamlit runtime 的 helper tests。
- 不修改 parser/normalizer/exporter/session contract。

非目標：
- 不做登入。
- 不做 Garmin Connect API。
- 不做資料庫。
- 不做雲端同步。
- 不做圖表分析。
- 不做 AI coaching。
- 不做 medical interpretation。
- 不做 HR zone。
- 不做 Garmin zone。
- 不做課表角色推論。
- 不做 planned workout matching。
- 不做 EXE 打包。
- 不做系統托盤。
- 不做自動開啟檔案總管。
- 不做多頁式完整產品 UI.
- 不新增除 Streamlit 以外的 dependencies.


## Phase 17：Improve Local UI Interaction Flow (post-MVP Local UI usability phase)

目標：
- 改善本機 Streamlit UI 的填寫體驗。
- 增加 input path 預檢、TCX 數量提示、預執行摘要、進階設定收合、錯誤訊息與 Markdown 下載。
- 保持 CLI、pipeline 與輸出契約不變。

完成條件：
- Input path 有即時檢查與友善訊息。
- Output folder 預設值穩定，且可重新產生。
- 基礎設定與進階設定分離。
- 執行前顯示設定摘要。
- 成功後可預覽與下載 Markdown。
- 失敗時顯示友善錯誤與技術細節。
- 新增 helper tests。
- 不新增 dependency。
- 不修改核心 pipeline / parser / normalizer / exporter / session contract。

非目標：
- 不做 native file picker。
- 不做 `st.file_uploader`。
- 不做 drag-and-drop upload。
- 不做自動開啟檔案總管。
- 不做 EXE 打包。
- 不做多頁式 UI。
- 不做圖表。
- 不做 AI coaching。
- 不做 Garmin Connect API。
- 不做資料庫。
- 不做雲端同步。
- 不做 HR zone / Garmin zone。
- 不做課表角色推論。
- 不做 planned workout matching。
- 不新增 dependencies。


## Phase 18：Improve Local UI Output Actions (post-MVP Local UI usability phase)

目標：
- 改善 Streamlit Local UI 的輸出結果操作。
- 讓使用者可直接複製三份輸出檔全文。
- 移除 Markdown download buttons。
- 新增打開輸出資料夾按鈕。
- 將預覽區調整為頁面最下方的滿版寬度且完整顯示。

完成條件：
- 可複製 `session_bundle.json`。
- 可複製 `session_bundle.md`。
- 可複製 `coach_handoff.md`。
- 可嘗試打開 output folder。
- output folder 開啟失敗時不會讓 UI crash。
- 頁面下方以寬版且完整長度（無內部滾動限制）預覽三個輸出檔案（JSON、Markdown、Coach Handoff）。
- 保留 output path 顯示。
- 新增 helper tests。
- 不新增 dependency。
- 不修改 pipeline / CLI / parser / normalizer / exporter / session contract。


## Phase 19：Copy Button Script Context Escape Hotfix (post-MVP Local UI usability phase)

目標：
- 修正 HTML/JS 複製按鈕在內文包含 `</` 時（例如 `</script>`）會提前閉合 Script 標籤的安全性與渲染錯誤問題。
- 套用標準 script-context 逸出 (escaping) 處理。

完成條件：
- 在 `ui_streamlit.py` 的 HTML/JS 複製按鈕 snippet 中，將 `</` 取代為 `<\/`。
- 複製按鈕可安全處理包含 Markdown 及 HTML 標籤的內容而不提前中斷 Script 區塊。


## Phase 20：Native Path Picker and Copy API Compatibility (post-MVP Local UI usability phase)

目標：
- 新增本機 native file/folder picker，降低手動輸入路徑負擔。
- 修正 copy-to-clipboard implementation，避免使用 deprecated Streamlit component HTML API。
- 保留手動路徑輸入與手動複製 fallback。

完成條件：
- 可用按鈕選擇單一 TCX 檔案。
- 可用按鈕選擇 TCX 資料夾。
- 可用按鈕選擇輸出資料夾。
- dialog 不可用或取消時 UI 不 crash。
- copy action 不使用 `st.components.v1.html` / `components.html`。
- 不再出現 `st.components.v1.html` deprecation warning。
- 若 clipboard copy 不可用，提供手動複製 fallback 說明。
- 不新增 dependencies。
- 不修改 pipeline / CLI / parser / normalizer / exporter / session contract。

Non-goals：
- 不做 file uploader。
- 不做 drag-and-drop upload。
- 不做 cloud upload。
- 不做 EXE 打包。
- 不做多頁式 UI。
- 不做圖表。
- 不做 AI coaching。
- 不做 Garmin Connect API。
- 不做資料庫。
- 不做雲端同步。
- 不做 HR zone / Garmin zone。
- 不做課表角色推論。
- 不做 planned workout matching。
- 不新增 dependencies。


## Phase 21：Release Candidate Validation and Documentation

目標：
- 停止功能擴充。
- 驗證目前 main 是否具備 local usable release 條件。
- 補齊 release validation、known limitations、manual smoke test checklist。
- 明確標示哪些是 release 內，哪些不是 release 內。

完成條件：
- 新增 release candidate validation 文件。
- 新增 known limitations 文件。
- README 更新目前 CLI / UI 使用方式。
- 架構文件補上 release boundary。
- 自動測試與 lint 狀態有紀錄。
- Windows manual smoke test checklist 有列出。
- 不修改核心 pipeline / CLI / parser / normalizer / exporter / session contract。


## Phase 24：Windows Local Launcher and Packaging Readiness

目標：
- 在正式 EXE 打包前，建立 Windows 本機啟動流程。
- 讓使用者不需要每次手動輸入長指令。
- 保持 `uv` 管理 Python 環境，不使用系統 Python。
- 補齊 packaging readiness 文件。

完成條件：
- 新增 `scripts/run_ui.cmd`。
- 新增 `scripts/run_cli_smoke.cmd`。
- 新增 `scripts/run_validation.cmd`。
- 新增 scripts 說明文件。
- 新增 Windows launcher / packaging readiness 文件。
- README 補上 Windows launcher 使用方式。
- 不建立 EXE。
- 不新增 dependency。
- 不修改 production code。


## Phase 25：Windows EXE Packaging

目標：
- 建立 Windows EXE packaging 流程與 kit。
- 支援 CLI 與 Local UI 的 PyInstaller spec 設定。
- 建立人工執行 build 的 CMD 腳本，避免 AI 執行 PyInstaller 造成 Token 消耗。
- 建立 smoke 測試與 clean 腳本。

完成條件：
- 新增 `src/garmin_tcx_ai/ui_exe_launcher.py` 作為 UI entry point。
- 新增 `packaging/garmin-tcx-ai-cli.spec` 與 `packaging/garmin-tcx-ai-ui.spec`。
- 新增 `packaging/version_info.txt` 規格。
- 新增 `scripts/build_exe.manual.cmd`。
- 新增 `scripts/smoke_exe.manual.cmd`。
- 新增 `scripts/clean_packaging_artifacts.cmd`。
- 新增 `docs/09_windows_exe_packaging.md` 文件。
- 更新 `.gitignore` 與 `RELEASE_NOTES.md`。
- Agent 不得執行 PyInstaller build，僅提供 packaging kit，實際 build 留給人類本機執行。
- 不新增 dependency，使用 `uv run --with pyinstaller pyinstaller ...`。
- 不修改核心邏輯與 output contract。





## Phase 26：Local Garmin Connect TCX Importer

目標：

- 新增 local-only optional CLI workflow：
  `Garmin Connect -> local TCX download folder -> pipeline.run_bundle()`。
- 使用 `python-garminconnect` 下載 TCX，但只放在 optional dependency group。
- 下載資料預設落在 `data/raw/garminconnect/`，再由既有 pipeline 輸出
  `session_bundle` 與可選的 `coach_handoff`。

完成條件：

- `pyproject.toml` 提供 `garminconnect` optional dependency group。
- 新增 `src/garmin_tcx_ai/importers/garminconnect_importer.py`。
- CLI 新增 `garmin-tcx-ai import-garminconnect` 子命令。
- 未安裝 optional dependency 時，core CLI 與 tests 不受影響；使用 importer 時給
  清楚安裝提示。
- Importer unit tests 使用 fake client，不呼叫真實 Garmin Connect API。
- CLI tests 驗證 importer 成功、importer 失敗、pipeline 失敗與既有 `bundle`
  行為。
- README 與 architecture docs 說明 local importer 的使用方式與安全邊界。

Non-goals：

- 不新增 Streamlit Garmin 登入 UI。
- 不新增 background scheduler。
- 不新增 database / SQLite / Grafana / InfluxDB。
- 不使用 official Garmin Developer Program API。
- 不新增 cloud sync、AI API upload、AI coaching 或 medical interpretation。
- 不解讀 HR zone / Garmin zone。
- 不做 planned workout matching 或 workout role inference。
- 不把 Garmin Connect dependency 打進 Windows EXE packaging kit。
- 不在 CI 跑真實 Garmin API integration tests。
