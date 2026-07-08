# Final Release Checklist

本文件提供 Garmin TCX AI v0.1.0 釋出前、中、後的完整手動與自動檢驗指南。

## 1. Release 前準備

請在 Windows 本機環境依序執行以下步驟：

1. 切換至 `main` 分支並拉取最新代碼：
   ```powershell
   git checkout main
   git pull
   ```
2. 確認 `git status` 乾淨，無任何未提交變更。
3. 同步包含選用依賴的開發環境：
   ```powershell
   uv sync --extra garminconnect
   ```
4. 執行完整自動化測試：
   ```powershell
   uv run --with pytest pytest -q
   ```
5. 執行 Ruff 靜態檢查：
   ```powershell
   uv run --with ruff ruff check src tests --no-cache
   ```
6. 執行手動 Windows EXE 編譯（此腳本會調用 PyInstaller 打包 CLI 與 UI 套件）：
   ```cmd
   scripts\build_exe.manual.cmd
   ```
7. 執行 EXE 基礎冒煙測試：
   ```cmd
   scripts\smoke_exe.manual.cmd
   ```

---

## 2. EXE 手動驗收 (Manual Validation)

編譯完成後，請手動進行以下功能驗證：

- [ ] **CLI 執行檔存在**：確認 `dist\garmin-tcx-ai\garmin-tcx-ai.exe` 存在。
- [ ] **UI 執行檔存在**：確認 `dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe` 存在。
- [ ] **CLI 基礎功能正常**：執行 CLI EXE 轉換測試 fixtures 能成功產出 session bundle。
- [ ] **CLI Garmin 導入指令正常**：執行以下指令可顯示說明文件且無錯誤：
  ```cmd
  dist\garmin-tcx-ai\garmin-tcx-ai.exe import-garminconnect --help
  ```
- [ ] **UI 啟動正常**：點兩下啟動 `dist\garmin-tcx-ai-ui\garmin-tcx-ai-ui.exe`，Streamlit 主控台與瀏覽器介面應成功開啟。
- [ ] **UI 資料來源切換**：介面最上方能正常切換「本機 TCX 檔案 / 資料夾」與「Garmin Connect 下載」兩種模式。
- [ ] **UI 本機模式正常**：在本機模式下，選擇或手動輸入包含 `tests/fixtures/minimal_running.tcx` 的路徑，能成功分析並在下方顯示預覽及提供複製。
- [ ] **UI Garmin Connect 模式欄位**：切換至 Garmin Connect 下載模式，能正常顯示 Email、Password、日期範圍、活動類型與下載資料夾等欄位。
- [ ] **UI Garmin Connect 下載驗證 (選用)**：若有真實帳號，可輸入並執行下載，確認資料能下載到 `data/raw/` 底下並自動分析。
- [ ] **Windows Credential Manager 金鑰庫儲存驗證 (選用)**：在 Garmin 模式下，儲存/讀取/刪除密碼功能與 Windows Credential Manager 能正常連動。

---

## 3. Release Artifact 打包與安全性規則

### 3.1 打包打包指令
本專案發行版本採用 `onedir` 目錄結構之 zip 壓縮檔。請在 PowerShell 執行以下命令打包發行檔：

```powershell
# 建立存放 zip 檔的目錄
New-Item -ItemType Directory -Force -Path release-artifacts | Out-Null

# 壓縮編譯產物及必要授權、說明文件
Compress-Archive `
  -Path dist\garmin-tcx-ai, dist\garmin-tcx-ai-ui, README.md, LICENSE, NOTICE.md, RELEASE_NOTES.md, docs\10_final_release_checklist.md `
  -DestinationPath release-artifacts\garmin-tcx-ai-v0.1.0-windows-onedir.zip `
  -Force
```

### 3.2 嚴格安全限制
> [!IMPORTANT]
> - `release-artifacts/` 目錄與產生的 `*.zip` 檔案**絕對不可 commit** 至 Git 儲存庫。
> - `dist/`、`build/`、`.packaging-logs/`、`*.exe` 亦**絕對不可 commit**。
> - zip 發行檔應手動上傳至 GitHub Release 頁面。

---

## 4. Git Tag 建立指引

建議的 Tag 名稱：`v0.1.0`

### 4.1 建立時機
1. 當 PR #29 (Final Release Preparation) 合併至 `main` 分支後。
2. 使用者在本機 `git checkout main` 並 `git pull` 同步最新狀態。
3. 執行前述 Release 前準備及手動驗收，確認 Zip artifact 包裝無誤。
4. 正式在本機打上 Tag 並推送到遠端。

> [!WARNING]
> 如果 tag `v0.1.0` 已經在遠端或本機存在，請勿強行覆蓋（`--force`），先停下來確認版本狀態。

### 4.2 建立指令
```powershell
git checkout main
git pull
git status
git tag -a v0.1.0 -m "Garmin TCX AI v0.1.0 local Windows release"
git push origin v0.1.0
```

---

## 5. GitHub Release 建議內容

請在 GitHub Release 建立新 Release：

- **Tag**: `v0.1.0`
- **Release Title**: `Garmin TCX AI v0.1.0`
- **Artifact**: 上傳手動打包的 `garmin-tcx-ai-v0.1.0-windows-onedir.zip`
- **Description 摘要範本**：
  ```markdown
  # Garmin TCX AI v0.1.0 - Local Windows Release

  個人 Garmin Connect 資料 ETL 與分析工具，支援 CLI 及 Streamlit 本機圖形化介面。

  ## 核心功能
  - CLI TCX bundle 彙整與分析
  - Streamlit 本機 UI 介面，內建原生路徑選取器、複製與預覽
  - Session bundle JSON / Markdown 及 AI 教練交接檔 (Coach handoff) 輸出
  - Garmin Connect 選用本機匯入器 (CLI 與 UI 整合模式)
  - 整合 Windows Credential Manager / 金鑰庫，安全儲存 Garmin 密碼
  - Windows onedir EXE 二進位免裝打包發行

  ## 授權與版權
  - MIT License
  - Copyright (c) 2026 Jia-Long Chen

  ## 專案邊界與已知限制 (Non-goals)
  - 本工具為 Local-only 應用，不包含雲端同步、外部資料庫、排程器。
  - 無 AI API upload 與自動 coaching。
  - 無醫學指標解讀、心率區間 / Garmin 區間推論、預計課表配對。
  - 不提供 EXE 安裝檔 (Installer) 或單一 exe (onefile)。
  - 真實 Garmin 登入及金鑰驗證屬本機手動選用功能。
  ```
