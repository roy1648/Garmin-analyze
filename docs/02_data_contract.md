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
  "trend_summary": {},
  "privacy": {},
  "data_quality": {},
  "ai_context": ""
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
- 估計爬升高度
- 單圈數量

### 5.2 趨勢摘要

MVP 趨勢欄位：

- 前半段平均配速
- 後半段平均配速
- 配速趨勢
- 前半段平均心率
- 後半段平均心率
- 心率趨勢

允許的簡單趨勢標籤：

- `faster_later`
- `slower_later`
- `stable`
- `insufficient_data`

趨勢計算規則：

- 可行時，以累積距離切分前半段與後半段。
- 前半段代表 0% 到 50% 距離；後半段代表 50% 到 100% 距離。
- 配速趨勢需要足夠的距離與時間資料。
- 心率趨勢需要足夠的心率與 trackpoint 資料。
- 距離、時間或 trackpoint 資料不足時，相關趨勢欄位應使用
  `insufficient_data`。

## 6. `ai_summary.md`

用途：交給 ChatGPT、Claude、NotebookLM 或類似 AI 工具的主要文件。

建議章節：

```markdown
# Running Activity Summary

## Activity

## Key Metrics

## Lap Summary

## Pace Trend

## Heart Rate Trend

## Elevation

## Data Quality Notes

## Privacy Notes

## Suggested AI Analysis Questions
```

Markdown 應該簡潔、基於事實，並避免假裝自己是認證教練或醫療專業人士。

## 7. 隱私契約

GPS policy 行為：

- `keep`：在 JSON、CSV 以及相關 AI 摘要中保留緯度與經度。
- `remove`：JSON 中將緯度與經度設為 `null`，CSV 中留空，Markdown 中省略路線細節。
- `redact_start_end`：預設以距離遮蔽活動前 300 公尺與後 300 公尺的
  GPS 座標。距離資料不足時，改遮蔽前 10% 與後 10% trackpoints。
  若活動太短，無法保留中段座標，則遮蔽所有 GPS 座標。

輸出必須記錄所選的 GPS policy。
