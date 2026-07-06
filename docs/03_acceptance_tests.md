# 驗收測試

本文件定義行為層級的驗收測試，不包含測試程式碼。

## 1. 單一 TCX 轉換

前提：有一個有效的 Garmin Connect Running TCX 檔案  
當：使用者轉換該檔案  
則：輸出目錄包含：

- `activity.json`
- `trackpoints.csv`
- `ai_summary.json`
- `ai_summary.md`

而且：原始 TCX 檔案沒有被修改。

## 2. 資料夾批次轉換

前提：有一個包含多個 `.tcx` 檔案的資料夾  
當：使用者轉換該資料夾  
則：每個有效的 Running TCX 檔案都會產生一組輸出檔案。

而且：非 TCX 檔案會被略過或提出警告，不會中止整個批次。

## 3. 只處理 Running 活動

前提：有一個 sport type 為 `Running` 的有效 TCX 檔案  
當：使用者轉換該檔案  
則：該檔案會被處理。

前提：有一個其他 sport type 的有效 TCX 檔案  
當：使用者轉換該檔案  
則：該檔案會被略過或拒絕，並顯示清楚的不支援活動警告。

## 4. 缺少心率

前提：有一個沒有心率資料的 Running TCX 檔案  
當：使用者轉換該檔案  
則：

- JSON 心率欄位為 `null`。
- CSV 心率儲存格為空。
- 如果無法計算 split 心率數值，AI 摘要以 `null` 與 notes 說明。
- 轉換不會失敗。

## 5. 缺少 GPS

前提：有一個沒有 GPS 座標的 Running TCX 檔案  
當：使用者轉換該檔案  
則：

- JSON 緯度與經度欄位為 `null`。
- CSV 緯度與經度儲存格為空。
- AI 摘要不包含 GPS 座標或路線細節。
- 轉換不會失敗。

## 6. 缺少海拔

前提：有一個沒有海拔資料的 Running TCX 檔案  
當：使用者轉換該檔案  
則：

- 海拔欄位為 `null` 或空白。
- 爬升高度為 `null`。
- AI 摘要包含海拔資料品質說明。
- 轉換不會失敗。

## 7. 多圈活動

前提：有一個包含多個 laps 的 Running TCX 檔案  
當：使用者轉換該檔案  
則：

- `activity.json` 依序包含所有 laps。
- `ai_summary.json` 包含 lap summaries。
- `ai_summary.md` 清楚呈現 lap summaries。

## 8. 無效 XML

前提：有一個副檔名為 `.tcx` 的 malformed XML 檔案  
當：使用者轉換該檔案  
則：

- 工具回報 invalid XML 錯誤。
- 不會為該檔案產生誤導性的部分輸出。
- 可行時，批次模式會繼續處理下一個檔案。

## 9. GPS Policy: keep

前提：有一個包含 GPS 資料的 Running TCX 檔案  
而且：GPS policy 是 `keep`  
當：使用者轉換該檔案  
則：

- `activity.json` 中有緯度與經度。
- `trackpoints.csv` 中有緯度與經度。
- `ai_summary.json` 將 `gps_policy` 記錄為 `keep`。
- `ai_summary.md` 包含說明 GPS 已保留的隱私備註。

## 10. GPS Policy: remove

前提：有一個包含 GPS 資料的 Running TCX 檔案  
而且：GPS policy 是 `remove`  
當：使用者轉換該檔案  
則：

- JSON 中的緯度與經度被移除或設為 `null`。
- CSV 中的緯度與經度儲存格為空。
- AI 摘要不暴露座標。
- `ai_summary.json` 將 `gps_policy` 記錄為 `remove`。

## 11. GPS Policy: redact_start_end

前提：有一個包含 GPS 資料的 Running TCX 檔案  
而且：GPS policy 是 `redact_start_end`  
當：使用者轉換該檔案  
則：

- 前 300 公尺與後 300 公尺的 GPS 座標會被遮蔽。
- 距離資料不足時，前 10% 與後 10% trackpoints 的 GPS 座標會被遮蔽。
- 如果活動太短，無法保留中段座標，所有 GPS 座標都會被遮蔽。
- AI 摘要記錄起點與終點路線資料已被遮蔽。

## 12. 輸出資料夾安全命名

前提：活動 ID 包含 path-unsafe characters  
當：使用者轉換該檔案  
則：

- 輸出資料夾使用 `safe_activity_id`。
- 原始 `activity_id` 仍保留在輸出 JSON 欄位中。
- 不安全字元會被替換，不會建立巢狀或非法路徑。

## 13. Warning schema

前提：轉換期間發現缺漏選填欄位或略過檔案  
當：工具記錄 warning  
則：warning 物件包含：

- `code`
- `severity`
- `field`
- `message`
- `source_file`

## 14. CLI exit codes

前提：所有輸入檔案成功轉換  
當：CLI 結束  
則：exit code 為 `0`。

前提：批次處理完成，但至少一個檔案失敗或被略過  
當：CLI 結束  
則：exit code 為 `1`。

前提：轉換開始前發生使用者、設定或輸入錯誤  
當：CLI 結束  
則：exit code 為 `2`。

## 15. Computed split metrics

前提：Running TCX 有足夠的距離、時間與 trackpoint 資料  
當：工具產生 AI-ready summary  
則：前半段與後半段以累積距離切分，並輸出配速與心率的純數值 delta。

前提：距離、時間或 trackpoint 資料不足  
當：工具產生 AI-ready summary  
則：受影響的數值欄位為 `null`，`data_available` 與 notes 說明資料狀態。

而且：輸出不包含 `faster_later`、`slower_later`、`stable`、疲勞、
表現或課表品質等語意解讀。

## 16. AI-ready Markdown

前提：有一次成功轉換  
當：開啟 `ai_summary.md`  
則：內容包含：

- 活動摘要
- 關鍵指標
- 單圈摘要
- Computed split metrics
- 海拔摘要
- 資料品質說明
- 隱私備註
- No-Inference Data Policy

而且：不包含 Suggested AI Analysis Questions 或其他主動分析問題。

## 17. No-Inference Policy

前提：有一個或多個已 normalize 的 TCX activities。

當：建立 summary 或 session bundle。
則：

- activity 與 lap 的 `role` 為 `null`。
- `role_source` 為 `not_inferred`。
- 不輸出課表角色、訓練目的、教練建議或醫療解讀。
- `data_policy` 明確記錄 no workout-role inference、no coaching advice
  與 no medical interpretation。
- 不輸出 Suggested AI Analysis Questions。

## 18. Multi-TCX session candidate grouping

前提：多個 activities 的 recorded start date 與 sport 相同，且相鄰
start time gap
不超過 30 分鐘。

當：建立 session bundle。
則：activities 依 start time 排序並進入同一個 session candidate。

前提：gap 超過 30 分鐘、sport 不同或 recorded start date 不同。

當：建立 session bundle。
則：建立不同 session candidates。

前提：activity 缺少 start time。

當：建立 session bundle。
則：該 activity 成為獨立 candidate，data quality 記錄缺漏。

每個 candidate 必須標示 `grouping_confidence: candidate` 與
`role_inference: disabled`。總距離、總時間、duration-weighted average HR
與 maximum HR 必須符合固定公式。

## 19. Session bundle exporters

前提：有多個已 normalize activities。

當：寫出 session bundle。
則：

- 產生 `session_bundle/session_bundle.json`。
- 產生 `session_bundle/session_bundle.md`。
- JSON 包含完整 top-level keys 與 data/privacy policy。
- Markdown 包含固定事實型章節。
- 兩個輸出均不含 GPS 座標、路線細節、課表角色推論、教練建議或
  Suggested AI Analysis Questions。

## 20. 完成條件

MVP 完成的條件：

- 有效的 Running TCX 檔案能成功轉換。
- 支援單一檔案與資料夾模式。
- 會產生四種輸出格式。
- 缺漏選填欄位不會造成轉換失敗。
- GPS policy 已實作並記錄。
- 原始 TCX 檔案永遠不會被修改。
- 上述驗收情境可以直接對應到 pytest 測試。
