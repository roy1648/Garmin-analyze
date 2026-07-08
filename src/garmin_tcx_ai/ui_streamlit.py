"""Streamlit UI for Garmin TCX AI Local Processing."""

from __future__ import annotations

from datetime import date, timedelta
import html
import json
from pathlib import Path

import streamlit as st

from garmin_tcx_ai.credentials import (
    get_stored_password,
    set_stored_password,
    delete_stored_password,
)
from garmin_tcx_ai.importers import (
    GarminConnectImportConfig,
    download_tcx_activities,
)
from garmin_tcx_ai.pipeline import BundleRunConfig, run_bundle
from garmin_tcx_ai.ui_helpers import (
    default_output_dir,
    inspect_input_path,
    normalize_output_path,
    open_folder,
    output_file_status,
    read_output_text,
    select_directory_dialog,
    select_tcx_file_dialog,
    validate_garmin_date_range,
    default_garmin_download_dir,
)


def render_copy_button_or_text_area(
    label: str, text: str, key: str
) -> None:
    """Render a copy action without deprecated Streamlit component APIs.

    Uses st.iframe (Streamlit >= 1.56) with a raw HTML/JS snippet to
    provide a browser-side clipboard copy button.  On clipboard API
    failure the JS status text instructs the user to use manual copy.

    Args:
        label: The button label text.
        text: The text to copy to the clipboard.
        key: A unique identifier used for HTML element IDs.
    """
    if not text:
        st.caption("無可複製內容。")
        return

    safe_label = html.escape(label)
    # Escape </ to <\/ so that </script> inside content cannot prematurely
    # close the enclosing <script> tag (standard script-context escaping).
    text_json = json.dumps(text).replace("</", r"<\/")
    key_safe = html.escape(key)

    st.iframe(
        f"""
        <button id="copy-{key_safe}" style="
            background: linear-gradient(135deg, #4f46e5, #0891b2);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        "> {safe_label} </button>
        <span id="copy-status-{key_safe}" style="
            margin-left: 8px;
            font-size: 13px;
            color: #10b981;
            font-family: system-ui, sans-serif;
            font-weight: 500;
        "></span>
        <script>
        const btn = document.getElementById("copy-{key_safe}");
        const status = document.getElementById("copy-status-{key_safe}");
        btn.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText({text_json});
                status.textContent = "已複製";
                setTimeout(() => {{
                    status.textContent = "";
                }}, 2000);
            }} catch (err) {{
                status.textContent = "複製失敗，請重試。";
            }}
        }};
        btn.onmouseover = () => {{
            btn.style.opacity = "0.9";
            btn.style.transform = "translateY(-0.5px)";
        }};
        btn.onmouseout = () => {{
            btn.style.opacity = "1";
            btn.style.transform = "none";
        }};
        </script>
        """,
        height=45,
    )


def _init_session_state() -> None:
    """Initialise stable session state keys if not already set."""
    if "default_output" not in st.session_state:
        st.session_state.default_output = str(default_output_dir())
    if "input_path_val" not in st.session_state:
        st.session_state.input_path_val = ""
    if "output_path_val" not in st.session_state:
        st.session_state.output_path_val = st.session_state.default_output


def _apply_dialog_result(dlg, state_key: str, notice_key: str) -> None:
    """Apply a DialogResult to session state from a widget on_click callback.

    Callbacks run before the script body re-executes, so it is safe here
    to assign ``st.session_state[state_key]`` even though a widget with
    that key will be instantiated later in the same rerun.
    """
    if dlg.success:
        st.session_state[state_key] = dlg.path_text
        st.session_state.pop(notice_key, None)
    else:
        level = "info" if "未選擇" in dlg.message else "warning"
        st.session_state[notice_key] = (level, dlg.message)


def _show_notice(notice_key: str) -> None:
    """Render a stored dialog notice, if any."""
    notice = st.session_state.get(notice_key)
    if notice is None:
        return
    level, message = notice
    if level == "info":
        st.info(message)
    else:
        st.warning(message)


def main() -> None:
    """Run the Streamlit Local UI application."""
    st.set_page_config(
        page_title="Garmin TCX AI Local UI",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #4f46e5, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: #6b7280;
            font-size: 1.0rem;
            margin-bottom: 2rem;
        }
        .stButton>button {
            background: linear-gradient(135deg, #4f46e5, #0891b2);
            color: white !important;
            border: none;
            padding: 0.6rem 1.8rem;
            border-radius: 0.5rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="main-title">Garmin TCX AI Local UI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">本機處理 Garmin TCX 檔案並產生 '
        "Coach-Facing Session Bundle</div>",
        unsafe_allow_html=True,
    )

    _init_session_state()

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("參數設定")

        # ── Data Source Mode ────────────────────────────────────────────────
        source_mode = st.radio(
            "資料來源",
            ["本機 TCX 檔案 / 資料夾", "Garmin Connect 下載"],
            index=0,
        )

        if source_mode == "本機 TCX 檔案 / 資料夾":
            # ── Input path ─────────────────────────────────────────────────────
            col_in, col_btn_file, col_btn_dir = st.columns(
                [3, 1, 1], vertical_alignment="bottom"
            )

            def _on_pick_tcx_file() -> None:
                _apply_dialog_result(
                    select_tcx_file_dialog(), "input_path_val", "_input_notice"
                )

            def _on_pick_tcx_dir() -> None:
                _apply_dialog_result(
                    select_directory_dialog("選擇包含 TCX 的資料夾"),
                    "input_path_val",
                    "_input_notice",
                )

            with col_btn_file:
                st.button(
                    "選擇 TCX 檔案",
                    key="btn_tcx_file",
                    on_click=_on_pick_tcx_file,
                )

            with col_btn_dir:
                st.button(
                    "選擇 TCX 資料夾",
                    key="btn_tcx_dir",
                    on_click=_on_pick_tcx_dir,
                )

            with col_in:
                input_path_str = st.text_input(
                    "Input path (TCX 檔案或資料夾路徑)",
                    help="指定單一 .tcx 檔案路徑，或包含 .tcx 檔案的資料夾路徑。",
                    key="input_path_val",
                )

            _show_notice("_input_notice")

            # Immediate input path validation
            path_status = inspect_input_path(input_path_str)
            if path_status.is_valid:
                st.success(path_status.message)
            else:
                if not input_path_str.strip():
                    st.warning(path_status.message)
                else:
                    st.error(path_status.message)
        else:
            # ── Garmin Connect ─────────────────────────────────────────────────
            garmin_email = st.text_input(
                "Garmin Connect email (電子郵件)",
                help="請輸入您的 Garmin Connect 登入電子郵件。",
            )

            col_pw_opt1, col_pw_opt2 = st.columns(2)
            with col_pw_opt1:
                use_stored_password = st.checkbox("使用已儲存密碼", value=True)
            with col_pw_opt2:
                remember_password = st.checkbox(
                    "將密碼儲存到 Windows Credential Manager", value=False
                )

            has_stored = False
            stored_pwd = None
            if garmin_email.strip():
                stored_pwd = get_stored_password(garmin_email.strip())
                has_stored = stored_pwd is not None

            if use_stored_password and has_stored:
                password_input = st.text_input(
                    "Garmin Connect password",
                    type="password",
                    placeholder="使用已儲存的密碼 (如需修改請在此輸入)",
                    help="系統憑證管理員中已有儲存此帳號的密碼。",
                )
                effective_password = (
                    password_input if password_input else stored_pwd
                )
            else:
                effective_password = st.text_input(
                    "Garmin Connect password",
                    type="password",
                    placeholder="請輸入密碼",
                )

            if st.button("刪除已儲存 Garmin 密碼"):
                if not garmin_email.strip():
                    st.error("請輸入 Garmin Connect email 以進行刪除。")
                else:
                    del_status = delete_stored_password(garmin_email.strip())
                    if not del_status.available:
                        st.error(del_status.message)
                    elif del_status.has_password:
                        st.error(del_status.message)
                    else:
                        st.success(del_status.message)

            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input(
                    "Start date (開始日期)",
                    value=date.today() - timedelta(days=6),
                )
            with col_end:
                end_date = st.date_input(
                    "End date (結束日期)",
                    value=date.today(),
                )

            activity_type = st.selectbox(
                "Activity type (活動類型)",
                ["running", "cycling", "walking", "hiking", "swimming"],
                index=0,
            )

            limit_val = st.number_input(
                "Limit (下載數量限制，可選)",
                min_value=0,
                value=0,
                step=1,
                help="限制下載的活動數量。設為 0 表示不限制。",
            )
            limit = int(limit_val) if limit_val > 0 else None

            overwrite = st.checkbox(
                "Overwrite existing TCX (覆寫已存在的 TCX 檔案)",
                value=False,
            )

            # Download folder path and directory picker
            col_dl_dir, col_btn_dl = st.columns(
                [3, 1], vertical_alignment="bottom"
            )
            default_dl = str(default_garmin_download_dir())

            def _on_pick_download_dir() -> None:
                _apply_dialog_result(
                    select_directory_dialog("選擇下載資料夾"),
                    "download_path_val",
                    "_download_notice",
                )

            if "download_path_val" not in st.session_state:
                st.session_state.download_path_val = default_dl

            with col_btn_dl:
                st.button(
                    "選擇下載資料夾",
                    key="btn_dl_dir",
                    on_click=_on_pick_download_dir,
                )
            with col_dl_dir:
                download_dir_str = st.text_input(
                    "Download folder (下載儲存資料夾)",
                    key="download_path_val",
                )
            _show_notice("_download_notice")

        # ── Output folder ──────────────────────────────────────────────────
        col_out, col_btn_out = st.columns(
            [3, 1], vertical_alignment="bottom"
        )

        def _on_pick_output_dir() -> None:
            _apply_dialog_result(
                select_directory_dialog("選擇輸出資料夾"),
                "output_path_val",
                "_output_notice",
            )

        def _on_reset_default_output() -> None:
            new_default = str(default_output_dir())
            st.session_state.default_output = new_default
            st.session_state.output_path_val = new_default

        with col_btn_out:
            st.button(
                "選擇輸出資料夾",
                key="btn_out_dir",
                on_click=_on_pick_output_dir,
            )

        with col_out:
            output_dir_str = st.text_input(
                "Output folder (輸出資料夾)",
                help="轉換後的結果儲存目錄。留空將使用自動產生的預設資料夾。",
                key="output_path_val",
            )

        _show_notice("_output_notice")

        st.button(
            "重新產生預設輸出資料夾", on_click=_on_reset_default_output
        )

        st.markdown("**輸出選項**")
        write_coach_handoff = st.checkbox(
            "Generate coach handoff (產生 coach_handoff.md)",
            value=True,
        )

        # Advanced Section inside expander
        with st.expander("進階設定", expanded=False):
            gps_policy = st.selectbox(
                "GPS Policy (GPS 隱私政策)",
                options=["redact_start_end", "remove", "keep"],
                index=0,
                help=(
                    "redact_start_end：建議預設，保留路線資訊但遮蔽起終點。\n"
                    "remove：移除 GPS 座標，隱私最高。\n"
                    "keep：保留 GPS 座標，僅在你確定要保留時使用。"
                ),
            )
            timezone_name = st.text_input(
                "Timezone (本地時區)",
                value="Asia/Taipei",
                help="指定時區名稱，例如 Asia/Taipei 或 UTC。",
            )
            max_gap_minutes = st.number_input(
                "Max gap minutes (活動分組間隔上限)",
                min_value=0,
                value=30,
                step=1,
                help="相同 local date 下分組 adjacent activities 的最大間隔。",
            )
            write_atomic = st.checkbox(
                "Generate atomic artifacts (產生詳細除錯檔)",
                value=False,
                help="Atomic artifacts：通常不需要，除非你要除錯或檢查原子輸出。",
            )

        # Pre-run Summary
        st.markdown("### 即將執行：")
        if source_mode == "本機 TCX 檔案 / 資料夾":
            tcx_desc = (
                f"{path_status.tcx_count} 個" if path_status.is_valid else "無效"
            )
            st.markdown(
                f"- **資料來源**: `本機 TCX`\n"
                f"- **Input**: `{input_path_str.strip() or '未填寫'}`\n"
                f"- **TCX count**: {tcx_desc}\n"
                f"- **Output**: `{output_dir_str.strip() or '將使用預設路徑'}`\n"
                f"- **GPS policy**: `{gps_policy}`\n"
                f"- **Coach handoff**: {'on' if write_coach_handoff else 'off'}\n"
                f"- **Atomic artifacts**: {'on' if write_atomic else 'off'}"
            )
        else:
            st.markdown(
                f"- **資料來源**: `Garmin Connect 下載`\n"
                f"- **Email**: `{garmin_email.strip() or '未填寫'}`\n"
                f"- **下載日期範圍**: `{start_date} ~ {end_date}`\n"
                f"- **活動類型**: `{activity_type}`\n"
                f"- **下載目錄**: `{download_dir_str.strip()}`\n"
                f"- **Output**: `{output_dir_str.strip() or '將使用預設路徑'}`\n"
                f"- **GPS policy**: `{gps_policy}`\n"
                f"- **Coach handoff**: {'on' if write_coach_handoff else 'off'}\n"
                f"- **Atomic artifacts**: {'on' if write_atomic else 'off'}"
            )

        if gps_policy == "keep":
            st.warning(
                "目前 GPS policy = keep，輸出可能保留完整座標。"
                "請確認你真的需要保留 GPS。"
            )

        st.markdown(
            "<div style='margin-top: 1.5rem;'></div>",
            unsafe_allow_html=True,
        )
        run_btn = st.button("開始轉換")

        if run_btn:
            if source_mode == "本機 TCX 檔案 / 資料夾":
                run_status = inspect_input_path(input_path_str)
                if not run_status.is_valid:
                    st.error(f"無法執行：{run_status.message}")
                    if "run_result" in st.session_state:
                        del st.session_state["run_result"]
                    if "import_result" in st.session_state:
                        del st.session_state["import_result"]
                else:
                    if "import_result" in st.session_state:
                        del st.session_state["import_result"]
                    from garmin_tcx_ai.pipeline import BundleRunResult
                    try:
                        normalized_out = normalize_output_path(output_dir_str)
                        config = BundleRunConfig(
                            input_path=Path(input_path_str.strip()),
                            output_dir=normalized_out,
                            gps_policy=gps_policy,
                            timezone_name=timezone_name.strip(),
                            max_gap_minutes=int(max_gap_minutes),
                            write_atomic=write_atomic,
                            write_coach_handoff=write_coach_handoff,
                        )
                        with st.spinner("執行轉換中..."):
                            result = run_bundle(config)
                    except Exception as exc:
                        try:
                            err_out = normalize_output_path(output_dir_str)
                        except Exception:
                            err_out = default_output_dir()
                        result = BundleRunResult(
                            success=False,
                            activity_count=0,
                            output_dir=err_out,
                            warning_messages=[],
                            error_message=f"無法建立輸出目錄或寫入檔案，請檢查權限與路徑是否正確：{exc}",
                        )
                    st.session_state.run_result = result
                    st.session_state.run_counter = (
                        st.session_state.get("run_counter", 0) + 1
                    )
            else:
                # Garmin Connect Mode
                if not garmin_email.strip():
                    st.error("無法執行：請輸入 Garmin Connect email。")
                elif not effective_password:
                    st.error("無法執行：請輸入密碼或啟用已儲存的密碼。")
                else:
                    date_status = validate_garmin_date_range(start_date, end_date)
                    if not date_status.is_valid:
                        st.error(f"無法執行：{date_status.message}")
                    else:
                        # Optional save password to keyring
                        if remember_password and effective_password:
                            save_status = set_stored_password(garmin_email.strip(), effective_password)
                            if save_status.has_password:
                                st.info("密碼已儲存到系統認證管理員。")
                            else:
                                st.warning("密碼無法儲存，將只用於本次執行。")

                        # Download
                        import_config = GarminConnectImportConfig(
                            start_date=start_date.strftime("%Y-%m-%d"),
                            end_date=end_date.strftime("%Y-%m-%d"),
                            activity_type=activity_type,
                            download_dir=Path(download_dir_str.strip()),
                            email=garmin_email.strip(),
                            password=effective_password,
                            limit=limit,
                            overwrite=overwrite,
                        )

                        with st.spinner("從 Garmin Connect 下載 TCX 檔案中..."):
                            import_result = download_tcx_activities(import_config)

                        st.session_state.import_result = import_result

                        if not import_result.success:
                            st.error(f"下載失敗：{import_result.error_message}")
                            if "run_result" in st.session_state:
                                del st.session_state["run_result"]
                        else:
                            from garmin_tcx_ai.pipeline import BundleRunResult
                            try:
                                normalized_out = normalize_output_path(output_dir_str)
                                config = BundleRunConfig(
                                    input_path=import_result.download_dir,
                                    output_dir=normalized_out,
                                    gps_policy=gps_policy,
                                    timezone_name=timezone_name.strip(),
                                    max_gap_minutes=int(max_gap_minutes),
                                    write_atomic=write_atomic,
                                    write_coach_handoff=write_coach_handoff,
                                )
                                with st.spinner("執行轉換與分析中..."):
                                    result = run_bundle(config)
                            except Exception as exc:
                                try:
                                    err_out = normalize_output_path(output_dir_str)
                                except Exception:
                                    err_out = default_output_dir()
                                result = BundleRunResult(
                                    success=False,
                                    activity_count=0,
                                    output_dir=err_out,
                                    warning_messages=[],
                                    error_message=f"無法建立輸出目錄或寫入檔案，請檢查權限與路徑是否正確：{exc}",
                                )
                            st.session_state.run_result = result
                            st.session_state.run_counter = (
                                st.session_state.get("run_counter", 0) + 1
                            )

    with col2:
        st.subheader("轉換結果")
        if "import_result" in st.session_state:
            imp_res = st.session_state.import_result
            st.markdown("### Garmin Connect 下載結果")
            if imp_res.success:
                st.success("🎉 下載成功！")
            else:
                st.error("❌ 下載失敗！")
            st.markdown(
                f"- **已下載活動**: {imp_res.downloaded_count}\n"
                f"- **已跳過活動**: {imp_res.skipped_count}\n"
                f"- **失敗活動**: {imp_res.failed_count}\n"
                f"- **下載目錄**: `{imp_res.download_dir.resolve()}`"
            )
            if imp_res.warning_messages:
                with st.expander("下載警告訊息", expanded=False):
                    for warning in imp_res.warning_messages:
                        st.warning(warning)
            if imp_res.error_message:
                st.error(imp_res.error_message)
            st.markdown("---")
        if "run_result" in st.session_state:
            res = st.session_state.run_result
            if res.success:
                st.success("🎉 轉換成功！")
                if res.warning_messages:
                    st.warning("執行過程中包含以下警告：")
                    for warning in res.warning_messages:
                        st.write(f"- {warning}")
                m1, m2 = st.columns(2)
                m1.metric("活動數量 (Activity Count)", res.activity_count)
                m2.metric(
                    "詳細除錯檔數量 (Atomic Artifacts)",
                    len(res.atomic_artifact_paths),
                )
                st.markdown("### 輸出路徑")
                st.code(str(res.output_dir.resolve()), language="text")
                if st.button("打開輸出資料夾"):
                    open_res = open_folder(res.output_dir)
                    if open_res.success:
                        st.success(open_res.message)
                    else:
                        st.error(open_res.message)
                st.markdown("### 輸出狀態")
                st.markdown(
                    "- **session_bundle.json**: "
                    f"{output_file_status(res.session_bundle_json_path)}"
                )
                st.markdown(
                    "- **session_bundle.md**: "
                    f"{output_file_status(res.session_bundle_markdown_path)}"
                )
                st.markdown(
                    "- **coach_handoff.md**: "
                    f"{output_file_status(res.coach_handoff_markdown_path)}"
                )
                st.markdown("### 複製輸出內容")
                run_key = st.session_state.get("run_counter", 0)
                render_copy_button_or_text_area(
                    "複製 session_bundle.json",
                    read_output_text(res.session_bundle_json_path),
                    f"session_bundle_json_{run_key}",
                )
                render_copy_button_or_text_area(
                    "複製 session_bundle.md",
                    read_output_text(res.session_bundle_markdown_path),
                    f"session_bundle_markdown_{run_key}",
                )
                if res.coach_handoff_markdown_path is not None:
                    render_copy_button_or_text_area(
                        "複製 coach_handoff.md",
                        read_output_text(res.coach_handoff_markdown_path),
                        f"coach_handoff_markdown_{run_key}",
                    )
                else:
                    st.info("本次未啟用 coach_handoff.md")
            else:
                st.error("❌ 轉換失敗！")
                st.error(
                    "轉換失敗，請先檢查 Input path、TCX 檔案格式、"
                    "Timezone 或輸出路徑。"
                )
                with st.expander("技術錯誤訊息", expanded=True):
                    st.code(
                        res.error_message or "無詳細錯誤訊息",
                        language="text",
                    )
                if res.warning_messages:
                    st.warning("警告：")
                    for warning in res.warning_messages:
                        st.write(f"- {warning}")
        else:
            st.info("尚未執行轉換。請設定左側參數，並點擊「開始轉換」按鈕。")

    # ── Full-width preview section ─────────────────────────────────────────
    if "run_result" in st.session_state:
        res = st.session_state.run_result
        if res.success:
            st.markdown("---")
            st.markdown("### 輸出檔案預覽")
            sb_json_text = read_output_text(res.session_bundle_json_path)
            sb_md_text = read_output_text(res.session_bundle_markdown_path)
            
            tab_names = ["session_bundle.json", "session_bundle.md"]
            has_handoff = res.coach_handoff_markdown_path is not None
            if has_handoff:
                tab_names.append("coach_handoff.md")
                ch_md_text = read_output_text(res.coach_handoff_markdown_path)
            
            tabs = st.tabs(tab_names)
            with tabs[0]:
                if sb_json_text:
                    st.code(sb_json_text, language="json")
                else:
                    st.write("未產生")
            with tabs[1]:
                if sb_md_text:
                    st.markdown(sb_md_text)
                else:
                    st.write("未產生")
            if has_handoff:
                with tabs[2]:
                    if ch_md_text:
                        st.markdown(ch_md_text)
                    else:
                        st.write("未產生")

    # Security: Redact any password key from session state
    for k in list(st.session_state.keys()):
        if "password" in k.lower():
            st.session_state[k] = ""


if __name__ == "__main__":
    main()
