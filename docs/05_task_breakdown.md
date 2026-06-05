# 任務拆解

本文件將未來實作拆成適合個人開發與 Codex Agent 協作的小任務。

本文件中的任何任務，都不應被解讀為可以超出 MVP 範圍過度建置。

## 階段 1：專案骨架

目標：

- 建立最小 Python 專案結構。

輸入：

- 現有規格文件。

輸出：

- Source folder。
- Script folder。
- Test folder。
- README 更新。

完成條件：

- 專案中已有清楚位置可放 parser、models、exporters、summaries 與 tests。
- 此階段尚不需要 TCX 轉換邏輯。

## 階段 2：Fixture 管理

目標：

- 建立安全的測試 fixture 處理方式。

輸入：

- 本機 Garmin TCX 範例。

輸出：

- `tests/fixtures/` 中用於提交的 minimal sanitized TCX fixture。
- `data/samples/` 中可選的本機樣本；此目錄必須保持 Git ignored。
- 明確規則：原始個人 TCX 檔案不得被修改。

完成條件：

- 可以撰寫測試，而不暴露不必要的個人 GPS 或健康資料。
- 測試不得依賴 `data/samples/` 中的本機私人資料。

## 階段 3：TCX Parser

目標：

- 將 Running TCX 檔案解析為原始結構化資料。

輸入：

- `.tcx` 檔案路徑。

輸出：

- 已解析的 activity、lap 與 trackpoint 資料。
- 對被略過或缺漏的選填欄位提出 warnings。

完成條件：

- 可以讀取 Running 活動欄位。
- Lap 與 trackpoint collections 保留原始順序。
- 無效 XML 會產生可讀的錯誤。
- Warnings 符合 `code`、`severity`、`field`、`message`、
  `source_file` schema。

## 階段 4：資料模型

目標：

- 定義內部 activity、lap、trackpoint、privacy 與 warning 結構。

輸入：

- Parser 輸出。

輸出：

- 正規化後的內部資料結構。

完成條件：

- 缺漏的標準欄位可以表示為 `None`。
- 公開結構使用 type hints。
- 資料名稱符合 `docs/02_data_contract.md`。

## 階段 5：JSON Exporter

目標：

- 寫出 `activity.json`。

輸入：

- 正規化活動資料。

輸出：

- 符合資料契約的 JSON。

完成條件：

- 輸出包含 `source`、`privacy`、`activity`、`laps`、`trackpoints`
  與 `warnings`。
- 缺漏值表示為 `null`。
- 輸出資料夾使用 `safe_activity_id`，不直接使用原始 `activity_id`。

## 階段 6：CSV Exporter

目標：

- 寫出 `trackpoints.csv`。

輸入：

- 正規化 trackpoint 資料。

輸出：

- 含必要標題列的 UTF-8 CSV。

完成條件：

- 必要欄位符合 `docs/02_data_contract.md`。
- 缺漏值變成空白儲存格。

## 階段 7：AI Summary Builder

目標：

- 建立 `ai_summary.json` 與 `ai_summary.md`。

輸入：

- 正規化活動資料。

輸出：

- 結構化 summary JSON。
- 簡潔 Markdown summary。

完成條件：

- 關鍵指標存在。
- 單圈摘要存在。
- 可行時，以距離切分前半段與後半段配速趨勢。
- 可行時，以距離切分前半段與後半段心率趨勢。
- 資料不足時，趨勢標示為 `insufficient_data`。
- 存在資料品質與隱私備註。

## 階段 8：批次處理

目標：

- 轉換資料夾中的所有 TCX 檔案。

輸入：

- 資料夾路徑。

輸出：

- 每個有效 Running TCX 都有一組輸出檔案。
- 對被略過的檔案提出 warnings。

完成條件：

- 可行時，單一壞檔案不會中止整個批次。
- CLI exit code 符合 `0` 全部成功、`1` 部分失敗或略過、
  `2` 轉換前輸入錯誤的慣例。

## 階段 9：驗收測試

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

## 階段 10：README

目標：

- 說明如何使用 MVP。

輸入：

- 可運作的轉換 script。

輸出：

- README，包含 setup、usage、examples、privacy warning 與 known limitations。

完成條件：

- 未來使用者可以根據 README 執行單一檔案與資料夾轉換。

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
