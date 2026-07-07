# 驗收測試

本文件列出 MVP 與 PR #9 的 acceptance criteria。測試不得依賴
`data/samples/` 的私人本機資料；真實 TCX 只能用於 local smoke test，
不得 commit。

## 1. Atomic Per-Activity Artifacts

每個 normalized Running TCX 可輸出：

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

這些 artifacts 用於 debug、audit 與資料交換，不是 AI coach-facing 的
主要輸出。

## 2. Coach-Facing Session Bundle

AI coach-facing 標準輸出為：

- `session_bundle/session_bundle.json`
- `session_bundle/session_bundle.md`

單一 TCX 與多個 TCX 都必須使用同一組 session bundle artifacts。

驗收條件：

- 單一 activity 時 `activity_count == 1`。
- 單一 activity 時 `session_candidate_count == 1`。
- 單一 activity 時 `contains_multiple_activities is False`。
- 多個 activity 仍保留每個 TCX 的 activity identity。
- JSON top-level schema 完整。

## 3. No-Inference Policy

Summary 與 session bundle 必須符合：

- 不包含 `Suggested AI Analysis Questions`。
- 不輸出 warmup、main set、cooldown、interval、tempo、easy、recovery、
  long run、quality session 等 role labels。
- 不輸出 coaching advice 或 medical interpretation。
- activity / lap role 為 `null`。
- `role_source == "not_inferred"`。
- `data_policy` 明確停用 workout-role inference、coaching advice 與
  medical interpretation。
- `computed_split_metrics.notes` 包含 fixed-formula disclaimer。

## 4. Computed Split Metrics

驗收條件：

- 不輸出 `faster_later`、`slower_later` 或 `stable`。
- Delta 計算式為 second half minus first half。
- Pace delta 單位為 seconds per km。
- Heart-rate delta 單位為 bpm。
- `interpretation_policy` 為
  `computed_metrics_only_no_training_interpretation`。
- `interpretation_level` 為
  `limited_for_interval_or_mixed_lap_activity`。
- 缺資料時相關數值為 `null`，並以 notes 說明缺漏。
- Notes 不得暗示 fatigue、collapse、workout quality、interval、
  tempo 或 easy。

## 5. Pace Reliability

Lap summary 必須驗證：

- Missing distance/duration -> `invalid` /
  `missing_distance_or_duration`。
- Non-positive distance/duration -> `invalid` /
  `non_positive_distance_or_duration`。
- Distance < 0.10 km -> `low` /
  `lap_distance_below_0.1km`。
- 0.10 km <= distance < 0.30 km -> `medium` /
  `lap_distance_between_0.1km_and_0.3km`。
- Distance >= 0.30 km -> `high` /
  `lap_distance_at_least_0.3km`。

## 6. Manual Context Placeholders

每個 session candidate 必須包含 `manual_context`：

- `planned_workout_text is None`
- `planned_workout_source == "manual_only"`
- `completion is None`
- `rpe_1_to_10 is None`
- pain before/during/after 為 `None`
- `next_day_status is None`

不得從 TCX 推論課表、完成度、疼痛、RPE 或隔日狀態。

## 7. Cadence / Power Factual Metrics

使用 synthetic trackpoints 驗證：

- Activity-level `key_metrics.cadence.avg_run_cadence_raw`。
- Activity-level `key_metrics.cadence.max_run_cadence_raw`。
- Activity-level `trackpoints_with_run_cadence_count`。
- Activity-level `key_metrics.power.avg_watts`。
- Activity-level `key_metrics.power.max_watts`。
- Lap-level cadence / power 依 `lap_index` 聚合。
- Session-level cadence / power 聚合所有 activity trackpoints。
- 缺資料時為 `null` 且 count 為 `0`。
- Cadence 不做 x2 conversion。
- `avg_cadence_spm is None`。
- `conversion_rule is None`。

## 8. Local Time / Timezone

驗收條件：

- UTC `start_time` 可轉為 `Asia/Taipei` local time。
- `local_date` 正確。
- Session grouping 使用 configured local date。
- `timezone_name` 可傳入 session bundle API 與 exporters。
- Invalid `timezone_name` raise `ValueError`。
- Markdown 顯示 timezone 與 local date。

## 9. Session Grouping

驗收條件：

- Activities 依 `start_time` 排序。
- 相同 local date、相同 sport、gap <= 30 min 時進入同一 candidate。
- gap > 30 min 時分成不同 candidate。
- 不同 sport 時分成不同 candidate。
- 缺少 `start_time` 時成為 singleton candidate。
- `grouping_confidence == "candidate"`。
- `role_inference == "disabled"`。
- Session total distance、duration、weighted HR、max HR 正確。
- Bundle 不包含 GPS 座標、route details 或 role inference。

## 10. Markdown Session Bundle

`session_bundle.md` 必須包含：

- `# TCX Session Bundle`
- `## Data Policy`
- `## Export Scope`
- `## Session Candidates`
- `## Activities`
- `## Lap Summaries`
- `## Computed Split Metrics`
- `## Data Quality`
- `## Privacy`

必須顯示：

- Manual context fields are placeholders only and were not inferred from TCX.
- Cadence values are raw Garmin RunCadence values; no cadence x2 conversion is applied.
- Local date。
- Timezone。
- Local start time。
- Average run cadence raw。
- Average watts。
- Pace reliability。
- Reliability reason。
- Avg cadence raw。
- Avg watts。
- Interpretation level。

不得新增 Suggested AI Analysis Questions。

## 11. Real Data Smoke Test

若本機有 git-ignored `data/samples/*.tcx`，可進行 local smoke test：

- Single-TCX bundle smoke。
- Multi-TCX bundle smoke。
- 輸出到 `data/processed/smoke_pr9/`。
- 驗證 GPS/privacy redaction。
- 驗證沒有 role inference。
- 驗證沒有 Suggested Questions。
- 驗證 cadence / power 欄位。
- 驗證 local time / timezone / local date。

Smoke output 與 raw Garmin data 不得 commit。

## 12. Verification Commands

PR #9 必須通過：

```powershell
uv run python -m pytest -q
uv run python -m ruff check src tests --no-cache
```

若 Windows sandbox 的 temp 權限造成 `WinError 5`，可指定 repo-local 或
其他可寫入 basetemp，例如：

```powershell
uv run python -m pytest -q --basetemp .pytest-tmp
```
