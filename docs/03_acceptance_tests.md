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
- 如果無法計算心率趨勢，AI 摘要包含資料品質說明。
- 轉換不會失敗。

## 5. 缺少 GPS

前提：有一個沒有 GPS 座標的 Running TCX 檔案  
當：使用者轉換該檔案  
則：

- JSON 緯度與經度欄位為 `null`。
- CSV 緯度與經度儲存格為空。
- AI 摘要說明無法進行路線分析。
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

- 活動開頭與結尾附近的 GPS 座標會被移除或遮蔽。
- 路線中段的 GPS 座標可以保留。
- AI 摘要記錄起點與終點路線資料已被遮蔽。

## 12. AI-ready Markdown

前提：有一次成功轉換  
當：開啟 `ai_summary.md`  
則：內容包含：

- 活動摘要
- 關鍵指標
- 單圈摘要
- 配速趨勢
- 心率趨勢
- 海拔摘要
- 資料品質說明
- 隱私備註
- 建議的 AI 分析問題

## 13. 完成條件

MVP 完成的條件：

- 有效的 Running TCX 檔案能成功轉換。
- 支援單一檔案與資料夾模式。
- 會產生四種輸出格式。
- 缺漏選填欄位不會造成轉換失敗。
- GPS policy 已實作並記錄。
- 原始 TCX 檔案永遠不會被修改。
- 上述驗收情境可以直接對應到 pytest 測試。
