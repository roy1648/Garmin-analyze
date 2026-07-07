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


## Phase 16：Minimal Streamlit Local UI

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


## Phase 17：Improve Local UI Interaction Flow

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


## Phase 18：Improve Local UI Output Actions

目標：
- 改善 Streamlit Local UI 的輸出結果操作。
- 讓使用者可直接複製三份輸出檔全文。
- 移除 Markdown download buttons。
- 新增打開輸出資料夾按鈕。
- 整合 OS 本機檔案與資料夾選取器（基於 `tkinter`）至輸入與輸出路徑設定中。
- 將 Markdown 預覽區調整為頁面最下方的滿版寬度且完整顯示。

完成條件：
- 可複製 `session_bundle.json`。
- 可複製 `session_bundle.md`。
- 可複製 `coach_handoff.md`。
- 可嘗試打開 output folder。
- output folder 開啟失敗時不會讓 UI crash。
- 可透過 UI 的「選擇檔案」和「選擇資料夾」按鈕開啟本機對話框選擇路徑。
- 頁面下方以寬版且完整長度（無內部滾動限制）預覽兩個 Markdown 檔案。
- 保留 output path 顯示。
- 新增 helper tests。
- 不新增 dependency。
- 不修改 pipeline / CLI / parser / normalizer / exporter / session contract。


