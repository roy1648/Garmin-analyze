# 資料契約

## 1. 輸入契約

### 1.1 支援的輸入

支援的輸入：

- Garmin Connect 匯出的 `.tcx` 檔案。

支援的活動類型：

- Running

輸入模式：

- 單一檔案路徑。
- 包含一個或多個 `.tcx` 檔案的資料夾路徑。

### 1.2 TCX 解析預期

解析器應支援：

- TCX XML namespaces。
- `TrainingCenterDatabase`。
- `Activities`。
- `Activity`。
- `Lap`。
- `Track`。
- `Trackpoint`。
- 已知且有用的 Garmin 擴充欄位。

已知 Garmin 擴充欄位可能包含：

- Speed
- Run cadence
- Average speed
- Average run cadence
- Watts

不支援的擴充欄位可以略過。

### 1.3 No-Inference Policy

本工具只輸出 TCX 原始欄位、由 TCX 數值以固定公式計算的結果、
資料品質標記、隱私策略與來源政策。無法由 TCX 欄位直接取得或以明確
公式計算的內容，不得自動產生。

- 不判斷活動、lap 或 segment 的課表角色與訓練目的。
- 不產生教練建議、醫療解讀、訓練處方或主動分析問題。
- `role` 固定為 `null`，`role_source` 固定為 `not_inferred`。
- 分組結果只可標示為 candidate，不可表示為來源資料中的事實。

## 2. 輸出檔案組

每個來源活動都應在輸出目錄下產生一組檔案。

建議命名模式：

```text
<safe_activity_id>/
  activity.json
  trackpoints.csv
  ai_summary.json
  ai_summary.md
```

`safe_activity_id` 必須由 `activity_id` 或來源檔名衍生。不得直接使用
原始 `activity_id` 作為資料夾名稱。產生規則：

- 將 path-unsafe characters 換成 `_`。
- 至少包含 Windows 與 POSIX 不安全字元：`< > : " / \ | ? *`。
- 去除前後空白與結尾的 `.`。
- 若結果為空，使用由來源檔名衍生出的安全檔名。

## 3. `activity.json`

用途：單一活動的完整結構化表示。

必要的頂層結構：

```json
{
  "source": {},
  "privacy": {},
  "activity": {},
  "laps": [],
  "trackpoints": [],
  "warnings": []
}
```

`warnings` 中每個物件必須符合以下 schema：

```json
{
  "code": "missing_optional_field",
  "severity": "warning",
  "field": "heart_rate_bpm",
  "message": "Heart rate is not available in the source file.",
  "source_file": "activity.tcx"
}
```

`severity` 可先使用 `info`、`warning` 或 `error`。
`field` 應填入受影響欄位；若 warning 是整個檔案層級，則使用 `null`。
`source_file` 應使用來源檔名，不應包含私人本機完整路徑。

### 3.1 `source`

```json
{
  "format": "tcx",
  "file_name": "activity.tcx",
  "file_path": "data/raw/activity.tcx"
}
```

### 3.2 `privacy`

```json
{
  "gps_policy": "keep"
}
```

允許的 `gps_policy` 值：

- `keep`
- `remove`
- `redact_start_end`

預設值：

- `keep`

### 3.3 `activity`

```json
{
  "sport": "Running",
  "activity_id": "2026-05-01T06:30:00Z",
  "start_time": "2026-05-01T06:30:00Z",
  "total_time_seconds": 3600.0,
  "distance_meters": 10000.0,
  "calories": 650,
  "average_heart_rate_bpm": 145,
  "maximum_heart_rate_bpm": 172,
  "maximum_speed_mps": 4.2
}
```

缺漏的標準值應為 `null`。

### 3.4 `laps`

每個 lap 物件：

```json
{
  "lap_index": 1,
  "start_time": "2026-05-01T06:30:00Z",
  "total_time_seconds": 1800.0,
  "distance_meters": 5000.0,
  "calories": 320,
  "average_heart_rate_bpm": 142,
  "maximum_heart_rate_bpm": 168,
  "maximum_speed_mps": 4.1,
  "intensity": "Active",
  "trigger_method": "Manual"
}
```

### 3.5 `trackpoints`

每個 trackpoint 物件：

```json
{
  "trackpoint_index": 1,
  "lap_index": 1,
  "timestamp": "2026-05-01T06:30:01Z",
  "latitude": 25.0,
  "longitude": 121.0,
  "altitude_meters": 20.5,
  "distance_meters": 10.0,
  "heart_rate_bpm": 140,
  "speed_mps": 2.8,
  "pace_seconds_per_km": 357.1,
  "run_cadence_spm": 170,
  "power_watts": 230
}
```

GPS 欄位取決於 `gps_policy`。

## 4. `trackpoints.csv`

用途：適合試算表與資料分析的 trackpoint 輸出。

必要欄位：

```text
activity_id
lap_index
trackpoint_index
timestamp
latitude
longitude
altitude_meters
distance_meters
heart_rate_bpm
speed_mps
pace_seconds_per_km
run_cadence_spm
power_watts
```

CSV 規則：

- 使用 UTF-8。
- 包含標題列。
- 缺漏值應為空白儲存格。
- GPS 欄位可能因 `gps_policy` 而為空。

## 5. `ai_summary.json`

用途：精簡、結構化、AI-ready 摘要。

必要的頂層結構：

```json
{
  "activity_summary": {},
  "key_metrics": {},
  "lap_summary": [],
  "computed_split_metrics": {},
  "privacy": {},
  "data_quality": {},
  "data_policy": {}
}
```

### 5.1 關鍵指標

MVP 關鍵指標：

- 持續時間，單位為分鐘
- 距離，單位為公里
- 平均配速，單位為每公里秒數
- 平均配速，格式為 `mm:ss/km`
- 平均心率
- 最大心率
- 最低海拔
- 最高海拔
- 估計爬升高度，並標記
  `sum_positive_consecutive_altitude_deltas` 計算方法
- 單圈數量

每筆 lap summary 必須包含：

```json
{
  "role": null,
  "role_source": "not_inferred"
}
```

### 5.2 Computed Split Metrics

前後半以累積距離 midpoint 切分，只輸出固定公式數值：

- 前半段平均配速
- 後半段平均配速
- 後半段配速 delta（後半減前半，單位為 seconds per km）
- 前半段平均心率
- 後半段平均心率
- 後半段心率 delta（後半減前半，單位為 bpm）

`faster_later`、`slower_later`、`stable` 與 `insufficient_data` 等語意
label 不再使用。`pace_data_available` 與 `heart_rate_data_available` 分別
標記兩組數值，兩者皆可用時 `data_available` 才是 `true`。無法計算的
數值為 `null`，`notes` 說明缺少 distance、timestamp 或 heart-rate data。

`interpretation_policy` 固定為
`computed_metrics_only_no_training_interpretation`。

### 5.3 Data Policy

`data_policy` 記錄來源為 `tcx_file`，允許 raw TCX fields、固定公式、
data-quality flags 與 privacy policy，並明確將 workout-role inference、
coaching advice 與 medical interpretation 設為停用。

## 6. `ai_summary.md`

用途：交給 ChatGPT、Claude、NotebookLM 或類似 AI 工具的主要文件。

建議章節：

```markdown
# Running Activity Summary

## Activity

## Key Metrics

## Lap Summary

## Computed Split Metrics

## Elevation

## Data Quality Notes

## Privacy Notes

## Data Policy
```

Markdown 必須簡潔、基於事實，不得包含 GPS 座標、路線細節、教練或醫療
建議，也不得包含 Suggested AI Analysis Questions 或任何主動分析問題。

## 7. 隱私契約

GPS policy 行為：

- `keep`：在 `activity.json` 與 CSV 保留緯度與經度；AI summary 與
  session bundle 仍不包含座標或路線細節。
- `remove`：JSON 中將緯度與經度設為 `null`，CSV 中留空，Markdown 中省略路線細節。
- `redact_start_end`：預設以距離遮蔽活動前 300 公尺與後 300 公尺的
  GPS 座標。距離資料不足時，改遮蔽前 10% 與後 10% trackpoints。
  若活動太短，無法保留中段座標，則遮蔽所有 GPS 座標。

輸出必須記錄所選的 GPS policy。

## 8. Multi-TCX Session Bundle

### 8.1 輸入與 identity

- 輸入為多個已 normalize 的 `ParsedActivity`。
- 一個 activity 永遠等於一個來源 TCX file，不合併 activity identity。
- 每個 activity 與 lap 的 `role` 為 `null`，`role_source` 為
  `not_inferred`。

### 8.2 Candidate grouping

activities 依 `start_time` 排序。相鄰 activities 只有同時符合以下規則才
放入同一個 session candidate：

- 相同 recorded start date（直接使用已記錄的 `start_time.date()`，不做
  timezone local conversion）。
- 相同 sport。
- 相鄰 `start_time` 間隔不超過 `max_gap_minutes`（預設 30）。

沒有 `start_time` 的 activity 必須是獨立 candidate，並在 data quality
記錄缺漏。所有 session 的 `grouping_confidence` 都是 `candidate`，
`role_inference` 都是 `disabled`。

### 8.3 輸出

```text
session_bundle/
  session_bundle.json
  session_bundle.md
```

JSON 必須包含 `schema_version`、`export_scope`、`data_policy`、`sessions`、
`data_quality` 與 `privacy`。Session totals 使用固定加總公式；平均心率使用
activity duration 加權；最大心率使用可用 activity maximum 的最大值。
兩種 bundle artifact 均不得包含 GPS 座標、路線細節、課表角色推論、
教練建議、醫療解讀或 Suggested AI Analysis Questions。
