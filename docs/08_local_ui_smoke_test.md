# Garmin TCX AI Local UI Smoke Test Guide

本指南提供本機 Streamlit UI 的人工煙霧測試 (Smoke Test) 與驗收流程。

## 0. 啟動 Local UI

請於專案目錄下執行以下指令啟動：

```powershell
uv run streamlit run src/garmin_tcx_ai/ui_streamlit.py
```

瀏覽器應會自動開啟 `http://localhost:8501`。

---

## 1. 人工驗證測試案例

### 1.1 選擇單一 TCX 檔案
1. 點擊左側「**選擇 TCX 檔案**」按鈕。
2. 於彈出的系統對話框中，選取 `tests/fixtures/minimal_running.tcx`。
3. 驗證：
   - 「Input path」文字欄位已更新為該檔案的絕對路徑。
   - 欄位下方顯示綠色提示語：`偵測到 1 個 TCX 檔案：minimal_running.tcx`。

### 1.2 選擇 TCX 資料夾
1. 點擊左側「**選擇 TCX 資料夾**」按鈕。
2. 於彈出的系統對話框中，選擇 `tests/fixtures` 目錄。
3. 驗證：
   - 「Input path」更新為資料夾絕對路徑。
   - 下方顯示綠色提示語：`偵測到 2 個 TCX 檔案。`。

### 1.3 預設輸出資料夾與唯一性
1. 點擊「**重新產生預設輸出資料夾**」按鈕。
2. 觀察「Output folder」欄位中的路徑。
3. 連續點擊數次，驗證：
   - 每次點擊均會產生不同的 timestamp 資料夾（格式包含微秒與 session 計數器，例如 `ui_run_20260708_092008_123456_1`）。
   - 連續點擊不易產生重複名稱。

### 1.4 自訂輸出資料夾
1. 點擊「**選擇輸出資料夾**」按鈕。
2. 選擇任意本機資料夾（例如 `data/processed`）。
3. 驗證「Output folder」已填入選取的路徑。
4. 手動在該欄位後加上一個不存在的子目錄（例如 `data/processed/smoke_run_1`），確認可直接編輯。

### 1.5 Coach Handoff 開關邏輯
- **案例 A：啟用（預設）**
  1. 勾選「Generate coach handoff (產生 coach_handoff.md)」。
  2. 點擊「開始轉換」。
  3. 驗證：
     - 右側顯示「複製 coach_handoff.md」按鈕與手動複製展開區。
     - 下方「輸出檔案預覽」預覽區包含 `coach_handoff.md` 的標籤頁 (Tab)。
- **案例 B：未啟用**
  1. 取消勾選「Generate coach handoff (產生 coach_handoff.md)」。
  2. 點擊「開始轉換」。
  3. 驗證：
     - 右側不顯示「複製 coach_handoff.md」按鈕與展開區。
     - 右側「複製輸出內容」最下方顯示簡短提示：`本次未啟用 coach_handoff.md`。
     - 下方「輸出檔案預覽」預覽區中不顯示 `coach_handoff.md` 的標籤頁（僅顯示 `session_bundle.json` 與 `session_bundle.md`）。

### 1.6 Atomic Artifacts 開關
- **案例 A：啟用**
  1. 展開「進階設定」，勾選「Generate atomic artifacts (產生詳細除錯檔)」。
  2. 點擊「開始轉換」。
  3. 驗證右側「詳細除錯檔數量 (Atomic Artifacts)」顯示大於 0 的數值。
- **案例 B：未啟用（預設）**
  1. 取消勾選「Generate atomic artifacts」。
  2. 點擊「開始轉換」。
  3. 驗證右側「詳細除錯檔數量 (Atomic Artifacts)」顯示為 0。

### 1.7 GPS Policy 警示
1. 展開「進階設定」。
2. 將「GPS Policy (GPS 隱私政策)」選單切換至 `keep`。
3. 驗證：參數設定區立即顯示黃色警告：`目前 GPS policy = keep，輸出可能保留完整座標。請確認你真的需要保留 GPS。`。

### 1.8 無效時區與錯誤提示
1. 展開「進階設定」。
2. 將「Timezone (本地時區)」欄位手動修改為無效名稱（例如 `Asia/Taipei_Invalid`）。
3. 點擊「開始轉換」。
4. 驗證：
   - 右側轉換結果顯示紅色失敗框：`❌ 轉換失敗！`。
   - 「技術錯誤訊息」展開區內包含錯誤原因：`Error: Invalid timezone name: Asia/Taipei_Invalid`。
   - Streamlit UI 未發生崩潰 (Crash)。

### 1.9 無效 TCX / 不支援運動
1. 將 Input path 設定為一個包含非 Running 活動的 TCX 檔案，或 malformed 檔案。
2. 點擊「開始轉換」。
3. 驗證右側錯誤訊息區域會顯示對應警告或排除訊息（例如 `Warning: Unsupported activity...`），且 UI 未發生崩潰。

### 1.10 複製按鈕與手動複製
1. 轉換成功後，點擊「複製 session_bundle.md」按鈕。
2. 驗證：
   - 按鈕右側顯示綠色 `已複製` 狀態，並在 2 秒後消失。
   - 嘗試貼上至文字編輯器，確認剪貼簿中已有該 Markdown 內容。
   - 點開下方的「複製 session_bundle.md（手動複製）」展開區，內有完整文字框可作為 fallback 手動複製。

### 1.11 開啟輸出資料夾與 Fallback
1. 轉換成功後，點擊「**打開輸出資料夾**」按鈕。
2. 驗證：
   - 若在支援此操作的本機 OS 上，檔案管理器（如 Windows 檔案總管）將開啟並定位至輸出目錄。
   - 若發生權限或系統不支援等原因，UI 不會崩潰，而是會在下方以紅色或黃色訊息提示使用者（例如無法開啟路徑，但可直接複製路徑手動開啟）。

### 1.12 輸出路徑不可寫入/權限錯誤處理
1. 手動將 Output folder 設為一個無效路徑或不可寫入目錄（例如 Windows 下的唯讀系統槽或無權限目錄 `C:\SystemVolumeInformation`，或包含無效字元的路徑）。
2. 點擊「開始轉換」。
3. 驗證：
   - 右側顯示紅色失敗框：`❌ 轉換失敗！`。
   - 「技術錯誤訊息」中清楚提示：`無法建立輸出目錄或寫入檔案，請檢查權限與路徑是否正確：[詳細 OSError]`。
   - Streamlit UI 未發生崩潰。
