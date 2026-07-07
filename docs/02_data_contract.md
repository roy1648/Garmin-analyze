# 資料契約

本專案 MVP 以 Garmin Connect 匯出的 Running TCX 為輸入，輸出
normalized activity、atomic per-activity artifacts，以及 coach-facing
session bundle artifacts。所有 AI-ready 輸出都必須遵守 No-Inference
Policy。

## 1. No-Inference Policy

本工具只輸出下列資料：

- TCX 原始欄位。
- 由 TCX 數值以固定公式計算的 metrics。
- data quality flags。
- privacy policy 與 source/data policy。
- time-gap rule 產生的 session candidate grouping。

不得自動產生下列內容：

- activity、lap 或 segment 的課表角色。
- warmup、main set、cooldown、interval、tempo、easy、recovery、
  long run、quality session 等訓練語意。
- fatigue、collapse、workout quality、workout type 等解讀。
- coaching advice、medical interpretation 或主動分析問題。

所有 activity 與 lap 的 role 欄位固定如下：

```json
{
  "role": null,
  "role_source": "not_inferred"
}
```

## 2. Coach-Facing 標準輸出

AI 教練或其他 AI 工具的標準輸出來源是 session bundle：

```text
session_bundle/
  session_bundle.json
  session_bundle.md
```

不論輸入是單一 TCX 或多個 TCX，都必須輸出同一組 session bundle
artifacts。單一 TCX 的 `export_scope` 範例如下：

術語說明：`session_bundle` 是 report/package format，可包含一個或多個
activity records，以及一個或多個 session candidates。它不代表多個 TCX
已被合併成一堂訓練；每個 TCX activity identity 必須保留，session
candidate 只表示候選分組。

```json
{
  "type": "session_bundle",
  "activity_count": 1,
  "session_candidate_count": 1,
  "contains_multiple_activities": false
}
```

Atomic per-activity artifacts 仍保留作為 debug、audit 與資料交換用途，
但不是 AI coach-facing 的主要輸出。

```text
<safe_activity_id>/
  activity.json
  trackpoints.csv
  ai_summary.json
  ai_summary.md
```

## 3. Atomic Activity Identity

- 一個 normalized activity 永遠等於一個來源 TCX file。
- Session bundle 不合併 activity identity。
- Session candidate grouping 只表示相鄰活動可能屬於同一訓練時段，
  不表示 TCX 來源資料已有該事實。

## 4. Session Bundle Schema

`session_bundle.json` top-level keys：

```json
{
  "schema_version": "tcx_training_data_v1",
  "export_scope": {},
  "data_policy": {},
  "sessions": [],
  "data_quality": {},
  "privacy": {}
}
```

`data_policy` 必須包含：

```json
{
  "activity_equals_one_tcx_file": true,
  "session_may_contain_multiple_activities": true,
  "grouping_is_candidate_not_fact": true,
  "no_workout_role_inference": true,
  "no_coaching_advice": true,
  "no_medical_interpretation": true,
  "manual_context_fields_are_placeholders": true
}
```

## 5. Session Candidate

每個 session candidate 必須包含：

- `session_id`
- `grouping_confidence: "candidate"`
- `grouping_rule`
- `role_inference: "disabled"`
- `activity_count`
- `start_time` / `end_time`
- `start_time_local` / `end_time_local`
- `timezone`
- `local_date`
- total distance / duration
- weighted average heart rate
- maximum heart rate
- cadence factual metrics
- power factual metrics
- `manual_context`
- `activities`
- `data_quality`

`manual_context` 固定為 manual-only placeholders：

```json
{
  "planned_workout_text": null,
  "planned_workout_source": "manual_only",
  "completion": null,
  "rpe_1_to_10": null,
  "pain_before": null,
  "pain_during": null,
  "pain_after": null,
  "next_day_status": null
}
```

這些欄位不得從 TCX 推論，也不得猜測課表完成度、疼痛、RPE 或隔日狀態。

## 6. Session Grouping

`build_session_bundle()` 使用 deterministic grouping rule：

- 依 `start_time` 排序。
- 使用 `timezone_name` 將 `start_time` 轉為 local date。
- 相同 local date。
- 相同 sport。
- 相鄰 `start_time` 間隔不超過 `max_gap_minutes`，預設 30 分鐘。
- 缺少 `start_time` 的 activity 必須獨立成為 singleton candidate。

`grouping_rule` 範例：

```json
{
  "same_local_date": true,
  "timezone": "Asia/Taipei",
  "same_sport": true,
  "max_gap_minutes": 30
}
```

無效的 `timezone_name` 必須 raise `ValueError`，不得靜默 fallback 成其他
timezone。

## 7. Activity Summary Local Time

每個 activity summary 必須保留 UTC time，並額外提供 local time 欄位：

```json
{
  "start_time": "2026-07-05T13:43:35Z",
  "start_time_local": "2026-07-05T21:43:35+08:00",
  "timezone": "Asia/Taipei",
  "local_date": "2026-07-05"
}
```

Timezone conversion 使用 Python standard library `zoneinfo`，不新增
production dependency。

## 8. Lap Pace Reliability

每個 lap summary 必須包含 `pace_reliability` 與 `reliability_reason`。
這是 data-quality flag，不是訓練解讀。

| 條件 | pace_reliability | reliability_reason |
|---|---|---|
| distance 或 duration 缺漏 | `invalid` | `missing_distance_or_duration` |
| distance <= 0 或 duration <= 0 | `invalid` | `non_positive_distance_or_duration` |
| distance < 0.10 km | `low` | `lap_distance_below_0.1km` |
| 0.10 km <= distance < 0.30 km | `medium` | `lap_distance_between_0.1km_and_0.3km` |
| distance >= 0.30 km | `high` | `lap_distance_at_least_0.3km` |

## 9. Computed Split Metrics

`computed_split_metrics` 只可輸出固定公式數值：

- 前半段平均配速。
- 後半段平均配速。
- 後半段配速 delta，計算式為後半減前半。
- 前半段平均心率。
- 後半段平均心率。
- 後半段心率 delta，計算式為後半減前半。

必要 policy 欄位：

```json
{
  "interpretation_policy": "computed_metrics_only_no_training_interpretation",
  "interpretation_level": "limited_for_interval_or_mixed_lap_activity"
}
```

`notes` 必須包含：

```text
This split metric is a fixed-formula summary and must not be interpreted as fatigue, workout quality, or workout type.
```

不得輸出 `faster_later`、`slower_later`、`stable`、`fatigue`、
`decline`、`collapse`、`tempo`、`interval`、`easy` 或 `main set`。

## 10. Cadence Factual Metrics

Cadence 使用 Garmin RunCadence 或 normalized trackpoint 中的原始數值，
本 PR 不做 x2 conversion。

Activity-level 範例：

```json
{
  "cadence": {
    "avg_run_cadence_raw": 83.1,
    "max_run_cadence_raw": 88,
    "trackpoints_with_run_cadence_count": 2485,
    "source": "tcx_extension_RunCadence_or_normalized_trackpoint",
    "avg_cadence_spm": null,
    "conversion_rule": null
  }
}
```

Lap-level `source` 使用 `normalized_trackpoints_by_lap`。Session-level
`source` 使用 `activity_trackpoint_aggregate`。

## 11. Power Factual Metrics

Power 使用 Garmin Watts 或 normalized trackpoint 中的原始數值，不推論
訓練強度。

```json
{
  "power": {
    "avg_watts": 230.5,
    "max_watts": 310,
    "trackpoints_with_power_count": 2485,
    "source": "tcx_extension_Watts_or_normalized_trackpoint"
  }
}
```

沒有 power 資料時，平均與最大值為 `null`，count 為 `0`。

## 12. Data Quality

Activity-level 與 session-level `data_quality` 必須包含：

- `trackpoints_with_run_cadence_count`
- `trackpoints_with_power_count`

Cadence 與 power 是 optional Garmin extensions，缺漏時不得列入
`missing_key_fields`。

## 13. Markdown Contract

`session_bundle.md` 必須包含：

- `# TCX Multi-Activity Report`
- `## Data Policy`
- `## Export Scope`
- `## Session Candidates`
- `## Activities`
- `## Lap Summaries`
- `## Computed Split Metrics`
- `## Data Quality`
- `## Privacy`

Data Policy 需明示：

- This report packages one or more TCX activities for AI-readable review.
  It does not merge them into one recorded workout.
- Session candidates are candidate activity groups for review; they do not
  merge activities into one recorded workout.
- Manual context fields are placeholders only and were not inferred from TCX.
- Cadence values are raw Garmin RunCadence values; no cadence x2 conversion is applied.

Markdown 不得包含 GPS 座標、route details、Suggested AI Analysis Questions、
訓練角色推論、教練建議或醫療解讀。

## 14. Privacy Contract

GPS policy 行為：

- `keep`：`activity.json` 與 CSV 可保留緯度與經度；AI summary 與
  session bundle 仍不得包含座標或路線細節。
- `remove`：JSON 中將緯度與經度設為 `null`，CSV 中留空。
- `redact_start_end`：遮蔽活動開頭與結尾的 GPS 座標。

輸出必須記錄所選 GPS policy。Raw TCX、`.env`、tokens、credentials、
`data/raw/` 與 `data/processed/` 不得 commit。
