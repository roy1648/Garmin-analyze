# 架構

本專案是個人 Garmin Connect TCX ETL 與 factual analysis 工具。MVP
範圍限定為手動匯出的 Running TCX，不包含 Web UI、database、Garmin API
login、AI API upload 或完整 AI coaching platform。

## 1. Artifact Layers

### 1.1 Atomic Per-Activity Artifacts

每個 TCX 可輸出一組 atomic artifacts：

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

這一層用於 debug、audit 與資料交換。

### 1.2 Coach-Facing Session Bundle Artifacts

AI 教練或 AI 工具的標準輸入是：

- `session_bundle/session_bundle.json`
- `session_bundle/session_bundle.md`

不論輸入是單一 TCX 或多個 TCX，都使用 session bundle 作為
coach-facing artifact。

## 2. Module Responsibility

```text
TCX file(s)
  -> parser.py
  -> normalizer.py
  -> privacy.py
  -> summary.py
  -> session.py
  -> exporters.py
```

### 2.1 `parser.py`

責任：

- 讀取 TCX XML。
- 處理 XML namespaces。
- 擷取 activity、lap、trackpoint 欄位。
- 擷取 Garmin extensions，例如 Speed、RunCadence、Watts。

Parser 不負責：

- 套用 privacy policy。
- 推論訓練角色。
- 產生 AI coaching 或 interpretation。

### 2.2 `normalizer.py`

責任：

- 將 parser output 轉為 normalized `ParsedActivity`。
- 缺漏欄位使用 `None`。
- 計算固定公式欄位，例如 pace。

Normalizer 不負責 session grouping 或 training interpretation。

### 2.3 `privacy.py`

責任：

- 套用 GPS policy。
- 支援 `keep`、`remove`、`redact_start_end`。
- 在輸出 metadata 中保留 privacy policy。

AI summary 與 session bundle 不得包含 GPS 座標或 route details。

### 2.4 `summary.py`

責任：

- 將單一 normalized activity 轉為 factual `ai_summary` dict。
- 計算 activity / lap / split / elevation / cadence / power factual metrics。
- 輸出 `data_policy` 與 `data_quality`。
- 產生 per-activity markdown summary。

Summary 不負責：

- AI coaching。
- 課表角色推論。
- 疲勞、訓練品質或訓練類型解讀。
- Suggested AI Analysis Questions。

### 2.5 `session.py`

責任：

- 接收一個或多個 normalized `ParsedActivity`。
- 依 `start_time` 排序。
- 使用 configured timezone 轉出 local date。
- 以 same local date、same sport、start-time gap 建立 session candidates。
- 保留每個 TCX 的 activity identity。
- 聚合 session-level factual metrics。
- 輸出 coach-facing `session_bundle` dict 與 markdown。

Session grouping 是 candidate，不是 TCX 來源中的事實，也不是課表角色
推論。

### 2.6 `exporters.py`

責任：

- 寫出 JSON / CSV / Markdown artifacts。
- `write_session_bundle_json()` 與 `write_session_bundle_markdown()` 寫到
  固定 `session_bundle/` 目錄。
- JSON 使用 UTF-8、indent=2，`None` 輸出為 `null`，datetime 輸出為
  ISO 8601。

Exporters 不解析 TCX，也不加入 business logic 或 inference。

## 3. Session Bundle API

```python
def build_session_bundle(
    activities: list[ParsedActivity],
    max_gap_minutes: int = 30,
    timezone_name: str = "Asia/Taipei",
) -> dict:
    ...
```

Exporter API：

```python
def write_session_bundle_json(
    activities: list[ParsedActivity],
    output_dir: Path,
    max_gap_minutes: int = 30,
    timezone_name: str = "Asia/Taipei",
) -> Path:
    ...

def write_session_bundle_markdown(
    activities: list[ParsedActivity],
    output_dir: Path,
    max_gap_minutes: int = 30,
    timezone_name: str = "Asia/Taipei",
) -> Path:
    ...
```

Timezone conversion 使用 Python standard library `zoneinfo`。無效
`timezone_name` 必須 raise `ValueError`。

## 4. Grouping Model

Session candidate grouping rules：

- Missing `start_time` -> singleton candidate。
- Same local date in configured timezone。
- Same sport。
- Adjacent start-time gap <= `max_gap_minutes`。

`grouping_rule` 必須明示：

```json
{
  "same_local_date": true,
  "timezone": "Asia/Taipei",
  "same_sport": true,
  "max_gap_minutes": 30
}
```

## 5. Factual Metrics

### 5.1 Pace Reliability

`summary.py` 在 lap summary 產生 `pace_reliability` 與
`reliability_reason`。這是 data-quality classification，不是訓練解讀。

### 5.2 Computed Split Metrics

Split metrics 只計算前後半固定公式數值。`interpretation_level` 固定為
`limited_for_interval_or_mixed_lap_activity`，並以 notes 明示不得解讀為
fatigue、workout quality 或 workout type。

### 5.3 Cadence / Power

Cadence 與 power 在 activity、lap、session 三層聚合：

- Activity-level 來源：`tcx_extension_RunCadence_or_normalized_trackpoint`
  與 `tcx_extension_Watts_or_normalized_trackpoint`。
- Lap-level 來源：`normalized_trackpoints_by_lap`。
- Session-level 來源：`activity_trackpoint_aggregate`。

Cadence 保留 raw Garmin RunCadence 值，不做 x2 conversion。

## 6. Data Safety

- 不得 commit raw TCX、`.env`、credentials、tokens。
- `data/raw/`、`data/processed/` 與 `data/samples/` 不進 Git。
- GPS coordinates 與 health metrics 視為 sensitive data。
- Tests 使用 committed sanitized fixtures。
- Unit tests 不得呼叫 Garmin Connect。

## 7. MVP Non-Goals

PR #9 與 MVP 不包含：

- Garmin Connect login。
- Garmin API。
- GarminDB。
- Database / SQLite。
- Web UI。
- Cloud sync。
- OpenAI、Claude、Gemini 或 NotebookLM API upload。
- AI coaching platform。
- Planned workout matching。
- Manual feedback input。
- HR zone / time in zone。
