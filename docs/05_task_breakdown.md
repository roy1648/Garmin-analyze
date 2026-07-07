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

