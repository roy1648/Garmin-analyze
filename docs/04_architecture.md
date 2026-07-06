# 架構

## 1. 設計原則

本專案應維持小型，並能由一位開發者維護。

MVP 應避免：

- 大型框架
- Web UI
- 資料庫儲存
- Garmin Connect 登入
- Garmin API 整合
- 直接上傳到 AI API

這些不是永久拒絕，而是延後到 TCX 轉換流程穩定之後再考慮。

## 2. MVP 元件

建議的未來 Python 結構：

```text
src/
  garmin_tcx_ai/
    parser.py
    models.py
    normalizer.py
    exporters.py
    summary.py
    session.py
    privacy.py
scripts/
  convert_tcx.py
tests/
  fixtures/
```

這是建議的實作結構，不是目前純文件階段的要求。

## 3. 元件職責

### 3.1 Parser

負責：

- 讀取 TCX XML。
- 處理 XML namespaces。
- 擷取 activity、lap 與 trackpoint 欄位。
- 擷取已知 Garmin 擴充欄位。
- 產生原始解析物件或 dictionaries。

Parser 不應：

- 寫入輸出檔案。
- 套用 AI 摘要邏輯。
- 修改 privacy policy。
- 判斷 activity、lap 或 segment 的訓練角色。

### 3.2 Normalizer

負責：

- 將解析後的 TCX 值轉換成內部資料契約。
- 正規化單位。
- 計算衍生值，例如配速。
- 保留缺漏值，稍後表示為 `null` 或空白儲存格。

### 3.3 Privacy

負責：

- 套用 GPS policy。
- 確保輸出記錄使用了哪一種 GPS policy。
- 避免 AI-ready 摘要意外洩漏座標。
- 對 `redact_start_end` 先使用距離遮蔽前後各 300 公尺，距離資料不足
  時才 fallback 到前後各 10% trackpoints。

支援的 policies：

- `keep`
- `remove`
- `redact_start_end`

### 3.4 Exporters

負責產生：

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`
- `session_bundle/session_bundle.json`
- `session_bundle/session_bundle.md`

Exporters 不應直接解析 TCX。

輸出資料夾必須使用 `safe_activity_id`，不得直接使用原始
`activity_id`。`safe_activity_id` 應將 path-unsafe characters 替換成
`_`。

### 3.5 Summary Builder

負責：

- 關鍵指標。
- 單圈摘要。
- 前半段與後半段的配速與心率固定公式數值及 delta。
- 資料品質說明。
- No-Inference Data Policy。

Summary builder 只輸出 TCX 原始欄位、固定公式結果與資料政策。不得產生
課表角色、語意 trend label、主動分析問題、教練建議或醫療解讀。

### 3.6 Session Bundle Builder

`session.py` 負責：

- 接收多個已 normalize 的 `ParsedActivity`。
- 依 start time 排序。
- 只用 same recorded start date、same sport 與相鄰 start-time gap 規則
  建立 session candidates；recorded start date 直接取自已記錄的
  `start_time.date()`，不執行 timezone local conversion。
- 保留一個 TCX file 等於一個 activity 的 identity。
- 以固定公式計算 session totals、duration-weighted average HR 與
  maximum HR。
- 產生不含 GPS 座標或路線細節的 Markdown。

Session builder 不判斷 workout 或 activity role。所有 grouping 都是
candidate，不是 TCX 來源中的事實；缺少 start time 時不得強行合併。

### 3.7 Script Entrypoint

MVP 可以從簡單 script 開始。

未來指令形式：

```bash
python scripts/convert_tcx.py --input data/raw/activity.tcx --output-dir data/processed --gps-policy keep
```

批次範例：

```bash
python scripts/convert_tcx.py --input data/raw --output-dir data/processed --gps-policy keep
```

Script 應設計成未來可以演進為正式 CLI，而不需要重寫核心邏輯。

Exit code 慣例：

- `0`：所有轉換都成功。
- `1`：批次已完成，但至少一個檔案失敗或被略過。
- `2`：轉換開始前發生使用者、設定或輸入錯誤。

## 4. 資料流程

```text
TCX file or folder
  -> input discovery
  -> TCX parser
  -> normalizer
  -> privacy policy
  -> per-activity summary builder
  -> optional session candidate builder for multiple normalized activities
  -> JSON / CSV / Markdown exporters
```

在整個流程中，原始 TCX 檔案都是唯讀。

邊界如下：parser 只解析來源欄位；normalizer 正規化與套用 privacy；
summary 建立單一 activity 的事實型資料；session 只做 candidate grouping
與固定公式聚合；exporters 只負責寫檔，不重新解析或推論。

## 5. 依賴策略

可行時，先從 Python standard library 開始。

未來可能的依賴：

- `pydantic`：用於更嚴格的資料模型。
- `pandas`：用於更完整的 CSV 或分析工作流程。
- `typer`：用於更完整的 CLI。
- `pytest`：用於自動化測試。

只有在依賴能降低複雜度，而不是增加複雜度時，才應加入。

## 6. 未來架構選項

### 6.1 個人資料庫

未來版本可以加入小型 SQLite 資料庫，用於：

- 活動歷史
- 趨勢分析
- 多活動比較
- 更快的本機查詢

這應該是在檔案式轉換穩定後的獨立階段。

### 6.2 GarminDB 研究

GarminDB 未來可評估作為 Garmin 資料匯入、SQLite 儲存、分析與
Jupyter-style 工作流程的參考或整合路徑。

MVP 不得依賴 GarminDB。

參考：

- https://github.com/tcgoetz/GarminDB

### 6.3 python-garminconnect 研究

python-garminconnect 未來可評估用於 Garmin Connect API 存取、活動資料、
健康資料、歷史資料與 token 工作流程。

MVP 不得登入 Garmin Connect，也不得依賴 python-garminconnect。

參考：

- https://github.com/cyberjunky/python-garminconnect

### 6.4 Web UI

Web UI 未來可能有用，但不屬於 MVP。

任何 UI 工作開始前，應先完成檔案式轉換流程。
