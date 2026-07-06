# 任務拆解

本文件將未來實作拆成適合個人開發與 Codex Agent 協作的小任務。

本文件中的任何任務，都不應被解讀為可以超出 MVP 範圍過度建置。

## 階段 1：專案骨架 ✅ COMPLETE

目標：

- 建立最小 Python 專案結構。

輸入：

- 現有規格文件。

輸出：

- Source folder (`src/garmin_tcx_ai/`)。
- Script folder (`scripts/`)。
- Test folder (`tests/`)。
- README 更新。

完成條件：✅

- 專案中已有清楚位置可放 parser、models、exporters、summaries 與 tests。
- 此階段尚不需要 TCX 轉換邏輯。

**Completed:** 2026-06-27. Project structure in place, `src/garmin_tcx_ai/` and test directories established.

## 階段 2：Fixture 管理 ✅ COMPLETE

目標：

- 建立安全的測試 fixture 處理方式。

輸入：

- 本機 Garmin TCX 範例。

輸出：

- `tests/fixtures/` 中用於提交的 minimal sanitized TCX fixture。
- `data/samples/` 中可選的本機樣本；此目錄必須保持 Git ignored。
- 明確規則：原始個人 TCX 檔案不得被修改。

完成條件：✅

- 可以撰寫測試，而不暴露不必要的個人 GPS 或健康資料。
- 測試不得依賴 `data/samples/` 中的本機私人資料。

**Completed:** 2026-06-27. `tests/fixtures/minimal_running.tcx` committed with sanitized data. `.gitignore` excludes `data/samples/` and `data/raw/`.

## 階段 3：資料模型 ✅ PARTIAL (Initial models only)

**Status:** 初始模型已存在，完整 normalizer 與驗證邏輯待實作。

目標：

- 定義內部 activity、lap、trackpoint、privacy 與 warning 結構。

輸入：

- Parser 輸出（待實作）。

輸出：

- 正規化後的內部資料結構。

完成條件：

- 缺漏的標準欄位可以表示為 `None`。
- 公開結構使用 type hints。
- 資料名稱符合 `docs/02_data_contract.md`。

**Progress:** `src/garmin_tcx_ai/models.py` created with baseline dataclass definitions. Awaiting TCX parser output to refine normalizer logic.

## 階段 4：TCX Parser ✅ 已實作

**Status:** 完整實作，multi-lap 聚合正確，測試覆蓋完整。

目標：

- 將 Running TCX 檔案解析為原始結構化資料。

輸入：

- `.tcx` 檔案路徑。

輸出：

- 已解析的 activity、lap 與 trackpoint 資料。
- 對被略過或缺漏的選填欄位提出 warnings。

完成條件：

- 可以讀取 Running 活動欄位。✅
- Lap 與 trackpoint collections 保留原始順序。✅
- 無效 XML 會產生可讀的錯誤。✅
- Warnings 符合 `code`、`severity`、`field`、`message`、
  `source_file` schema。✅

**實作狀態（2026-06-27 修正版本）：**

- `src/garmin_tcx_ai/parser.py` 實作完成。
- `parse_tcx()` 回傳 `ParsedActivity`，覆蓋 activity、lap、
  trackpoint 與 Garmin extension 欄位（Speed、RunCadence、Watts）。
- Multi-lap aggregate 正確性：activity-level totals 由 lap 聚合推導
  （總和），不從 Lap descendants 直接取值。
- `TCXParseError` 處理無效 XML；`UnsupportedActivityError` 處理
  非 Running 活動。
- 測試覆蓋：`tests/test_parser.py`（23 個 single-lap 與錯誤情境測試）
  與 `tests/test_parser_multilap.py`（12 個 multi-lap 聚合測試）。
- `tests/fixtures/two_lap_running.tcx` 提供 multi-lap 測試覆蓋
  （兩圈、共 4 個 trackpoints，驗證 total/distance/calories 加總、
  max speed/HR 取最大、avg HR 取平均）。
- Ruff lint 通過，無錯誤。

## 階段 5：Normalizer 與隱私 ✅ 已實作

**Status:** 完整實作，GPS privacy 三種 policy 皆有測試覆蓋。

目標：

- 將解析後的 TCX 值轉換成內部資料契約。
- 正規化單位並計算衍生值（如配速）。

輸入：

- Parser 輸出。

輸出：

- 符合 `docs/02_data_contract.md` 的正規化資料。

完成條件：

- 缺漏的標準欄位可以表示為 `None`。✅
- 公開結構使用 type hints。✅
- Privacy policy 可被正確套用。✅

**實作狀態（PR #5）：**

- `src/garmin_tcx_ai/normalizer.py`：`normalize_activity(parsed, gps_policy)`
  回傳 copy，不修改輸入；缺漏值保留 `None`；`source.file_name` 與
  warnings 只保留檔名不含路徑；`speed_mps > 0` 時補算
  `pace_seconds_per_km`；保留 `datetime` 物件交由 exporter 序列化。
- `src/garmin_tcx_ai/privacy.py`：`apply_gps_policy()` 支援 `keep`、
  `remove`、`redact_start_end`（距離優先、10% fallback、太短則全遮蔽），
  回傳 copy 不 mutate 輸入。
- `tests/test_normalizer.py`、`tests/test_privacy.py` 覆蓋完整。

## 階段 6：JSON Exporter ✅ 已實作

**Status:** 完整實作於 `src/garmin_tcx_ai/exporters.py`。

目標：

- 寫出 `activity.json`。

輸入：

- 正規化活動資料。

輸出：

- 符合資料契約的 JSON。

完成條件：

- 輸出包含 `source`、`privacy`、`activity`、`laps`、`trackpoints`
  與 `warnings`。✅
- 缺漏值表示為 `null`。✅
- 輸出資料夾使用 `safe_activity_id`，不直接使用原始 `activity_id`。✅

**實作狀態（PR #5）：** `write_activity_json()` 輸出六個頂層 keys，
`None` → JSON `null`，`datetime` → ISO 8601 字串（`Z` 結尾），資料夾名稱
由 `safe_activity_id()` 衍生。`tests/test_exporters.py` 覆蓋。

## 階段 7：CSV Exporter ✅ 已實作

**Status:** 完整實作於 `src/garmin_tcx_ai/exporters.py`。

目標：

- 寫出 `trackpoints.csv`。

輸入：

- 正規化 trackpoint 資料。

輸出：

- 含必要標題列的 UTF-8 CSV。

完成條件：

- 必要欄位符合 `docs/02_data_contract.md`。✅
- 缺漏值變成空白儲存格。✅

**實作狀態（PR #5）：** `write_trackpoints_csv()` 依契約順序輸出 13 欄
UTF-8 CSV，缺漏值為空白 cell，GPS 欄位反映目前 privacy policy。
`tests/test_exporters.py` 覆蓋。

## 階段 8：AI Summary Builder ✅ 已實作

**Status:** 完整實作，單元測試與真實資料 smoke test 皆通過。

目標：

- 建立 `ai_summary.json` 與 `ai_summary.md`。

輸入：

- 正規化活動資料。

輸出：

- 結構化 summary JSON。
- 簡潔 Markdown summary。

完成條件：

- 關鍵指標存在。✅
- 單圈摘要存在。✅
- 可行時，以距離切分前半段與後半段配速趨勢。✅
- 可行時，以距離切分前半段與後半段心率趨勢。✅
- 資料不足時，趨勢標示為 `insufficient_data`。✅
- 存在資料品質與隱私備註。✅

**實作狀態（PR #8）：**

- `src/garmin_tcx_ai/summary.py`：`build_ai_summary()` 純資料轉換，
  產生七個頂層 key（`activity_summary`、`key_metrics`、`lap_summary`、
  `computed_split_metrics`、`privacy`、`data_quality`、`data_policy`）；
  `render_ai_summary_markdown()` 產生固定章節的事實型 Markdown。
- Phase 9 起，split 以距離 midpoint 切分前半 / 後半，只保留固定公式
  metrics 與 second-half delta，不再輸出語意 label。海拔 gain 只加總正向
  上升並明確標記 computed method，有效點不足 2 個為 `None`。
- `src/garmin_tcx_ai/exporters.py`：新增 `write_ai_summary_json()` 與
  `write_ai_summary_markdown()`，沿用既有 `safe_activity_id` 資料夾，
  `None` → JSON `null`，`datetime` → ISO 8601（`Z` 結尾），UTF-8。
- summary 與 markdown 皆不輸出 GPS 座標或路線細節，不含教練 / 醫療建議。
- 測試：`tests/test_summary.py`（37 個測試）與擴充的
  `tests/test_exporters.py`。真實 TCX smoke test 產生四個檔案且無 GPS 洩漏。

## 階段 9：Multi-TCX Session Bundle 與 No-Inference Policy ✅ 已實作

**Status:** 完成實作與自動化測試；CLI 不在本階段範圍。

目標：

- 將多個已 normalize TCX activities 建立成 AI 可讀的事實型 session
  bundle。
- 收斂 single-activity summary，移除語意 trend labels 與 Suggested AI
  Analysis Questions。
- 明確禁止 workout-role inference、教練建議與醫療解讀。

輸入：

- 多個已 normalize 的 `ParsedActivity`。
- 可調整的 `max_gap_minutes`，預設 30。

輸出：

- `session_bundle/session_bundle.json`。
- `session_bundle/session_bundle.md`。
- 更新後的 no-inference `ai_summary.json` 與 `ai_summary.md`。

完成條件：

- 一個 TCX file 永遠保留為一個 activity。✅
- 同 local date、同 sport、相鄰 start-time gap 不超過門檻時，才放入
  同一 candidate。✅
- 缺少 start time 時為獨立 candidate 並記錄 data quality。✅
- Grouping 明確標示 candidate，role inference 明確停用。✅
- Session totals、duration-weighted average HR 與 maximum HR 使用固定公式。✅
- Summary 與 bundle 均不含 GPS 座標、路線細節、課表角色推論、
  Suggested AI Analysis Questions、教練建議或醫療解讀。✅
- pytest 與 Ruff 驗證通過。✅

刻意不包含：CLI、batch CLI command、Garmin API、database、Web UI、
AI API upload、weekly summary、HR zone、planned workout matching 或任何
訓練處方。

## 階段 10：驗收測試

目標：

- 將 `docs/03_acceptance_tests.md` 轉換成自動化測試。

輸入：

- Fixtures。
- 轉換程式碼。

輸出：

- pytest test suite。

完成條件：

- 覆蓋主要成功與失敗情境。
- 測試確認原始 TCX 檔案不會被修改。

## 階段 11：README

目標：

- 說明如何使用 MVP。

輸入：

- 可運作的轉換 script。

輸出：

- README，包含 setup、usage、examples、privacy warning 與 known limitations。

完成條件：

- 未來使用者可以根據 README 執行單一檔案與資料夾轉換。

---

## MVP 開發守則

**PR 提交必須遵循 AGENTS.md 中的 PR Operating Rules：**

1. **One PR = One Objective** — 不在同一個 PR 中混合 parser、exporter、privacy、summary、CLI、batch 工作。
2. **PR 模板** — 每個 PR 必須明確說明 objective、allowed files、forbidden files、non-goals 與 verification commands。
3. **嚴格遵守 MVP 非目標** — 參考 `docs/06_mvp_freeze.md`，不實作 Garmin API、資料庫、Web UI、AI API 上傳或其他超出範圍的功能。
4. **衝突報告** — 如果文件與實作狀態衝突，在 PR 描述中報告衝突，而不是擴大範圍。

---

## 未來任務

這些任務刻意排除在 MVP 之外。

### SQLite Activity Store

研究並設計個人 SQLite 資料庫，用於多活動歷史與趨勢分析。

在檔案式轉換穩定前，不要開始。

### GarminDB 研究

評估 GarminDB 作為參考或可能整合路徑。

研究問題：

- 它是否會重複或取代本機 TCX parser？
- 它能否協助 SQLite 活動歷史？
- 對個人專案而言，它是否增加太多操作複雜度？

參考：

- https://github.com/tcgoetz/GarminDB

### python-garminconnect 研究

評估 python-garminconnect 供未來 Garmin Connect API 存取使用。

研究問題：

- 需要哪些 authentication 與 token handling？
- 哪些 activity 與 health endpoints 有用？
- API 存取會帶來哪些 privacy 與 reliability 風險？

參考：

- https://github.com/cyberjunky/python-garminconnect

### Web UI

只在以下條件成立後再考慮：

- TCX 轉換穩定。
- 輸出契約已證明有用。
- 使用者有重複工作流程，足以支持 UI 投資。
