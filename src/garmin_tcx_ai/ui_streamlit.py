"""Streamlit UI: turn Garmin running TCX files into AI-readable text.

The page has three steps: choose the data source (Garmin Connect
download or local TCX files), choose the output folder, then run.
The result is a folder with ``summary.txt``, ``all_in_one.txt`` and one
``runs/*.txt`` file per run, all previewable and copyable in the page.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import streamlit as st

from garmin_tcx_ai.ai_text import DENSITY_CHOICES
from garmin_tcx_ai.credentials import (
    delete_stored_password,
    get_stored_password,
    set_stored_password,
)
from garmin_tcx_ai.importers import (
    GarminConnectImportConfig,
    download_tcx_activities,
)
from garmin_tcx_ai.pipeline import (
    BundleRunConfig,
    BundleRunResult,
    run_bundle,
)
from garmin_tcx_ai.ui_helpers import (
    default_garmin_download_dir,
    default_output_dir,
    inspect_input_path,
    normalize_output_path,
    open_folder,
    read_output_text,
    select_directory_dialog,
    select_tcx_file_dialog,
    validate_garmin_date_range,
)

SOURCE_GARMIN = "Garmin Connect 下載"
SOURCE_LOCAL = "本機 TCX 檔案 / 資料夾"

DENSITY_LABELS = {
    "standard": "標準（建議）",
    "compact": "精簡（檔案最小）",
    "detailed": "詳細（保留最多軌跡點）",
}


def render_copy_button_or_text_area(
    label: str, text: str, key: str
) -> None:
    """Render a browser-side clipboard copy button.

    Uses st.iframe (Streamlit >= 1.56) with a raw HTML/JS snippet. On
    clipboard API failure the status text asks the user to copy manually.

    Args:
        label: The button label text.
        text: The text to copy to the clipboard.
        key: A unique identifier used for HTML element IDs.
    """
    if not text:
        st.caption("無可複製內容。")
        return

    safe_label = html.escape(label)
    # Escape </ so that </script> inside content cannot close the tag.
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
                setTimeout(() => {{ status.textContent = ""; }}, 2000);
            }} catch (err) {{
                status.textContent = "複製失敗，請改用下載或手動選取。";
            }}
        }};
        </script>
        """,
        height=45,
    )


def _today() -> date:
    """Return today's date in the machine's local timezone."""
    return datetime.now(UTC).astimezone().date()


def _init_session_state() -> None:
    """Initialise stable session state keys if not already set."""
    defaults = {
        "default_output": str(default_output_dir()),
        "input_path_val": "",
        "download_path_val": str(default_garmin_download_dir()),
        "pwd_counter": 0,
        "garmin_start": _today() - timedelta(days=6),
        "garmin_end": _today(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "output_path_val" not in st.session_state:
        st.session_state.output_path_val = st.session_state.default_output


def _apply_dialog_result(dlg, state_key: str, notice_key: str) -> None:
    """Apply a DialogResult to session state from an on_click callback."""
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


def _set_recent_days(days: int) -> None:
    """Callback: set the Garmin date range to the last *days* days."""
    st.session_state.garmin_end = _today()
    st.session_state.garmin_start = _today() - timedelta(days=days - 1)


def _failed_result(output_dir_str: str, exc: Exception) -> BundleRunResult:
    """Build a failed BundleRunResult for unexpected exceptions."""
    try:
        err_out = normalize_output_path(output_dir_str)
    except Exception:  # noqa: BLE001 - keep the UI alive on any error
        err_out = default_output_dir()
    return BundleRunResult(
        success=False,
        activity_count=0,
        output_dir=err_out,
        warning_messages=[],
        error_message=(
            "無法建立輸出目錄或寫入檔案，請檢查權限與路徑是否正確："
            f"{exc}"
        ),
    )


def _store_run_result(result: BundleRunResult) -> None:
    """Persist a run result and bump the run counter."""
    st.session_state.run_result = result
    st.session_state.run_counter = (
        st.session_state.get("run_counter", 0) + 1
    )


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _render_local_source() -> str:
    """Render the local TCX path picker and return the path text."""
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
        st.button("選擇 TCX 檔案", key="btn_tcx_file",
                  on_click=_on_pick_tcx_file)
    with col_btn_dir:
        st.button("選擇 TCX 資料夾", key="btn_tcx_dir",
                  on_click=_on_pick_tcx_dir)
    with col_in:
        input_path_str = st.text_input(
            "TCX 檔案或資料夾路徑",
            help="指定單一 .tcx 檔案，或包含 .tcx 檔案的資料夾（只掃描第一層）。",
            key="input_path_val",
        )
    _show_notice("_input_notice")

    path_status = inspect_input_path(input_path_str)
    if path_status.is_valid:
        st.success(path_status.message)
    elif not input_path_str.strip():
        st.info(path_status.message)
    else:
        st.error(path_status.message)
    return input_path_str


def _render_garmin_source() -> dict:
    """Render Garmin Connect login and date range; return the settings."""
    garmin_email = st.text_input(
        "Garmin Connect 帳號 (Email)",
        help="登入 Garmin Connect 用的電子郵件。",
    )

    email_key = garmin_email.strip()
    stored_pwd = None
    if email_key:
        # Only hit the OS keyring when the email actually changes.
        if st.session_state.get("_stored_pwd_cache_email") != email_key:
            st.session_state._stored_pwd_cache_email = email_key
            st.session_state._stored_pwd_cache_value = (
                get_stored_password(email_key)
            )
        stored_pwd = st.session_state._stored_pwd_cache_value
    has_stored = stored_pwd is not None

    pw_key = f"garmin_password_raw_{st.session_state.pwd_counter}"
    if has_stored:
        st.caption("此帳號已有儲存的密碼，留空即使用儲存的密碼。")
        password_input = st.text_input(
            "Garmin Connect 密碼",
            type="password",
            placeholder="使用已儲存的密碼（要更換請在此輸入）",
            key=pw_key,
        )
        effective_password = password_input or stored_pwd
    else:
        effective_password = st.text_input(
            "Garmin Connect 密碼",
            type="password",
            placeholder="請輸入密碼",
            key=pw_key,
        )

    col_remember, col_delete = st.columns([2, 1])
    with col_remember:
        remember_password = st.checkbox(
            "登入成功後把密碼存到 Windows 認證管理員",
            value=not has_stored,
            help="密碼只存在系統認證管理員，不會寫入任何專案檔案。",
        )
    with col_delete:
        if has_stored and st.button("刪除已儲存密碼"):
            del_status = delete_stored_password(email_key)
            if del_status.success:
                st.session_state.pop("_stored_pwd_cache_email", None)
                st.session_state.pop("_stored_pwd_cache_value", None)
                st.success(del_status.message)
                st.rerun()
            else:
                st.error(del_status.message)

    st.markdown("**日期範圍**")
    q1, q2, q3, q4 = st.columns(4)
    q1.button("最近 7 天", on_click=_set_recent_days, args=(7,),
              use_container_width=True)
    q2.button("最近 14 天", on_click=_set_recent_days, args=(14,),
              use_container_width=True)
    q3.button("最近 28 天", on_click=_set_recent_days, args=(28,),
              use_container_width=True)
    q4.button("最近 90 天", on_click=_set_recent_days, args=(90,),
              use_container_width=True)
    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input("開始日期", key="garmin_start")
    with col_end:
        end_date = st.date_input("結束日期", key="garmin_end")

    date_status = validate_garmin_date_range(start_date, end_date)
    if not date_status.is_valid:
        st.error(date_status.message)

    return {
        "email": email_key,
        "password": effective_password,
        "remember": remember_password,
        "start_date": start_date,
        "end_date": end_date,
        "date_valid": date_status.is_valid,
    }


def _render_output_and_advanced(source_mode: str) -> dict:
    """Render the output folder picker and advanced settings."""
    col_out, col_btn_out, col_btn_reset = st.columns(
        [3, 1, 1], vertical_alignment="bottom"
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
        st.button("選擇輸出資料夾", key="btn_out_dir",
                  on_click=_on_pick_output_dir)
    with col_btn_reset:
        st.button("用新的預設資料夾", on_click=_on_reset_default_output)
    with col_out:
        output_dir_str = st.text_input(
            "輸出資料夾",
            help="產生的 txt 檔會放在這裡。留空會自動建立一個帶時間戳的資料夾。",
            key="output_path_val",
        )
    _show_notice("_output_notice")

    with st.expander("進階設定（通常不用改）", expanded=False):
        density_label = st.selectbox(
            "軌跡取樣密度",
            options=[DENSITY_LABELS[d] for d in DENSITY_CHOICES],
            index=list(DENSITY_CHOICES).index("standard"),
            help=(
                "短圈（間歇）自動保留較密的軌跡點，長圈較疏。"
                "「詳細」檔案較大，「精簡」最小。"
            ),
        )
        density = next(
            key for key, label in DENSITY_LABELS.items()
            if label == density_label
        )
        timezone_name = st.text_input(
            "時區", value="Asia/Taipei",
            help="本地日期與時間使用的時區，例如 Asia/Taipei 或 UTC。",
        )

        st.markdown("**Garmin Connect 下載選項**")
        activity_type = st.selectbox(
            "活動類型",
            ["running", "cycling", "walking", "hiking", "swimming"],
            index=0,
            help="目前文字報告只針對跑步設計；其他類型僅供下載。",
        )
        col_dl_dir, col_btn_dl = st.columns(
            [3, 1], vertical_alignment="bottom"
        )

        def _on_pick_download_dir() -> None:
            _apply_dialog_result(
                select_directory_dialog("選擇下載資料夾"),
                "download_path_val",
                "_download_notice",
            )

        with col_btn_dl:
            st.button("選擇下載資料夾", key="btn_dl_dir",
                      on_click=_on_pick_download_dir)
        with col_dl_dir:
            download_dir_str = st.text_input(
                "TCX 下載資料夾", key="download_path_val",
                help="下載的原始 TCX 會存在這裡，之後可離線重複使用。",
            )
        _show_notice("_download_notice")
        col_limit, col_over = st.columns(2)
        with col_limit:
            limit_val = st.number_input(
                "下載數量上限（0 = 不限制）", min_value=0, value=0, step=1
            )
        with col_over:
            overwrite = st.checkbox("覆寫已存在的 TCX 檔案", value=False)

        st.markdown("**舊版輸出（預設不產生）**")
        write_session_bundle = st.checkbox(
            "session_bundle.json / .md", value=False
        )
        write_coach_handoff = st.checkbox(
            "coach_handoff.md（會一併產生 session_bundle）", value=False
        )
        write_atomic = st.checkbox(
            "每筆活動的除錯檔（activity.json、trackpoints.csv…）",
            value=False,
        )
        gps_policy = st.selectbox(
            "舊版輸出的 GPS 政策",
            options=["redact_start_end", "remove", "keep"],
            index=0,
            help="只影響舊版輸出與除錯檔；txt 文字檔一律不含 GPS 座標。",
        )
        max_gap_minutes = st.number_input(
            "舊版 session 分組間隔上限（分鐘）",
            min_value=0, value=30, step=1,
        )

    return {
        "output_dir_str": output_dir_str,
        "density": density,
        "timezone_name": timezone_name.strip(),
        "activity_type": activity_type,
        "download_dir_str": download_dir_str,
        "limit": int(limit_val) if limit_val > 0 else None,
        "overwrite": overwrite,
        "write_session_bundle": write_session_bundle,
        "write_coach_handoff": write_coach_handoff,
        "write_atomic": write_atomic,
        "gps_policy": gps_policy,
        "max_gap_minutes": int(max_gap_minutes),
    }


def _bundle_config(input_path: Path, settings: dict) -> BundleRunConfig:
    """Build the pipeline config from UI settings."""
    return BundleRunConfig(
        input_path=input_path,
        output_dir=normalize_output_path(settings["output_dir_str"]),
        gps_policy=settings["gps_policy"],
        timezone_name=settings["timezone_name"],
        max_gap_minutes=settings["max_gap_minutes"],
        write_atomic=settings["write_atomic"],
        write_coach_handoff=settings["write_coach_handoff"],
        write_ai_text=True,
        write_session_bundle=settings["write_session_bundle"],
        trackpoint_density=settings["density"],
    )


def _run_local(input_path_str: str, settings: dict) -> None:
    """Run the pipeline for a local TCX path."""
    st.session_state.pop("import_result", None)
    status = inspect_input_path(input_path_str)
    if not status.is_valid:
        st.error(f"無法執行：{status.message}")
        st.session_state.pop("run_result", None)
        return
    try:
        config = _bundle_config(Path(input_path_str.strip()), settings)
        with st.spinner("產生文字檔中..."):
            result = run_bundle(config)
    except Exception as exc:  # noqa: BLE001 - surface any error in UI
        result = _failed_result(settings["output_dir_str"], exc)
    _store_run_result(result)


def _run_garmin(garmin: dict, settings: dict) -> None:
    """Download from Garmin Connect, then run the pipeline."""
    if not garmin["email"]:
        st.error("無法執行：請輸入 Garmin Connect 帳號。")
        return
    if not garmin["password"]:
        st.error("無法執行：請輸入密碼。")
        return
    if not settings["download_dir_str"].strip():
        st.error("無法執行：請填寫下載資料夾（進階設定）。")
        return
    if not garmin["date_valid"]:
        st.error("無法執行：日期範圍不正確。")
        return

    st.session_state.pop("import_status_msg", None)
    import_config = GarminConnectImportConfig(
        start_date=garmin["start_date"].strftime("%Y-%m-%d"),
        end_date=garmin["end_date"].strftime("%Y-%m-%d"),
        activity_type=settings["activity_type"],
        download_dir=Path(settings["download_dir_str"].strip()),
        email=garmin["email"],
        password=garmin["password"],
        limit=settings["limit"],
        overwrite=settings["overwrite"],
    )
    with st.spinner("從 Garmin Connect 下載 TCX 檔案中..."):
        import_result = download_tcx_activities(import_config)

    # Persist the password only after a successful login so a typo is
    # never saved.
    if import_result.success and garmin["remember"]:
        save_status = set_stored_password(
            garmin["email"], garmin["password"]
        )
        if save_status.success:
            st.session_state._stored_pwd_cache_email = garmin["email"]
            st.session_state._stored_pwd_cache_value = garmin["password"]
            st.session_state.import_status_msg = (
                "info", "密碼已儲存到系統認證管理員。"
            )
        else:
            st.session_state.import_status_msg = (
                "warning",
                f"密碼無法儲存，只用於本次執行：{save_status.message}",
            )

    old_key = f"garmin_password_raw_{st.session_state.pwd_counter}"
    st.session_state.pwd_counter += 1
    st.session_state.pop(old_key, None)
    st.session_state.import_result = import_result

    if not import_result.success:
        st.session_state.pop("run_result", None)
        st.rerun()

    try:
        config = _bundle_config(import_result.download_dir, settings)
        with st.spinner("產生文字檔中..."):
            result = run_bundle(config)
    except Exception as exc:  # noqa: BLE001 - surface any error in UI
        result = _failed_result(settings["output_dir_str"], exc)
    _store_run_result(result)
    st.rerun()


def _render_import_result() -> None:
    """Show the Garmin Connect download outcome, if any."""
    msg = st.session_state.get("import_status_msg")
    if msg is not None:
        level, text = msg
        (st.info if level == "info" else st.warning)(text)
    imp = st.session_state.get("import_result")
    if imp is None:
        return
    if imp.success:
        st.success(
            f"Garmin Connect 下載完成：新下載 {imp.downloaded_count}、"
            f"已存在略過 {imp.skipped_count}、失敗 {imp.failed_count}。"
        )
    else:
        st.error("Garmin Connect 下載失敗。")
    if imp.error_message:
        st.error(imp.error_message)
    if imp.warning_messages:
        with st.expander("下載警告訊息", expanded=False):
            for warning in imp.warning_messages:
                st.warning(warning)


def _render_run_result() -> None:
    """Show the pipeline outcome with previews and copy/download."""
    res = st.session_state.get("run_result")
    if res is None:
        return
    st.markdown("---")
    st.subheader("3. 結果")

    if not res.success:
        st.error("產生失敗。請檢查來源路徑、TCX 檔案、時區或輸出資料夾。")
        with st.expander("技術錯誤訊息", expanded=True):
            st.code(res.error_message or "無詳細錯誤訊息", language="text")
        for warning in res.warning_messages:
            st.warning(warning)
        return

    st.success(f"完成！已處理 {res.activity_count} 次跑步。")
    for warning in res.warning_messages:
        st.warning(warning)

    m1, m2, m3 = st.columns(3)
    m1.metric("跑步次數", res.activity_count)
    m2.metric("每次跑步 txt", len(res.run_txt_paths))
    m3.metric("合併總檔", "1" if res.all_in_one_txt_path else "0")

    st.code(str(res.output_dir.resolve()), language="text")
    if st.button("打開輸出資料夾"):
        open_res = open_folder(res.output_dir)
        (st.success if open_res.success else st.error)(open_res.message)

    run_key = st.session_state.get("run_counter", 0)
    summary_text = read_output_text(res.summary_txt_path)
    all_text = read_output_text(res.all_in_one_txt_path)

    st.markdown("**餵給 AI**：最簡單的做法是複製或下載 `all_in_one.txt`。")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        render_copy_button_or_text_area(
            "複製 all_in_one.txt", all_text, f"all_in_one_{run_key}"
        )
    with c2:
        st.download_button(
            "下載 all_in_one.txt", data=all_text,
            file_name="all_in_one.txt", mime="text/plain",
            disabled=not all_text, key=f"dl_all_{run_key}",
        )
    with c3:
        st.download_button(
            "下載 summary.txt", data=summary_text,
            file_name="summary.txt", mime="text/plain",
            disabled=not summary_text, key=f"dl_sum_{run_key}",
        )

    tab_summary, tab_runs, tab_all = st.tabs(
        ["摘要 summary.txt", "每次跑步 runs/", "全部 all_in_one.txt"]
    )
    with tab_summary:
        st.code(summary_text or "未產生", language="text")
    with tab_runs:
        if res.run_txt_paths:
            names = [p.name for p in res.run_txt_paths]
            picked = st.selectbox("選擇一次跑步", names,
                                  key=f"run_pick_{run_key}")
            path = res.run_txt_paths[names.index(picked)]
            run_text = read_output_text(path)
            render_copy_button_or_text_area(
                f"複製 {picked}", run_text, f"run_copy_{run_key}"
            )
            st.code(run_text or "未產生", language="text")
        else:
            st.write("未產生")
    with tab_all:
        st.code(all_text or "未產生", language="text")

    legacy = [
        ("session_bundle.json", res.session_bundle_json_path),
        ("session_bundle.md", res.session_bundle_markdown_path),
        ("coach_handoff.md", res.coach_handoff_markdown_path),
    ]
    legacy_written = [(n, p) for n, p in legacy if p is not None]
    if legacy_written or res.atomic_artifact_paths:
        with st.expander("舊版輸出", expanded=False):
            for name, path in legacy_written:
                st.markdown(f"- `{name}`：`{path.resolve()}`")
            if res.atomic_artifact_paths:
                st.markdown(
                    f"- 除錯檔：{len(res.atomic_artifact_paths)} 個"
                )


def _scrub_passwords(source_mode: str) -> None:
    """Drop raw password keys once the Garmin form is not in use."""
    current = f"garmin_password_raw_{st.session_state.get('pwd_counter', 0)}"
    keep_current = source_mode == SOURCE_GARMIN
    for key in list(st.session_state.keys()):
        if "password" in key.lower() and not (
            keep_current and key == current
        ):
            st.session_state.pop(key, None)


def main() -> None:
    """Run the Streamlit Local UI application."""
    st.set_page_config(
        page_title="Garmin 跑步記錄 → AI 文字檔",
        page_icon="🏃",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title("Garmin 跑步記錄 → AI 文字檔")
    st.caption(
        "一次抓下指定期間的跑步 TCX，轉成 AI 好讀的純文字檔："
        "一份摘要（週跑量、心率等）＋每次跑步一份記錄＋一份合併總檔。"
        "全程在本機執行，不上傳任何資料。"
    )
    _init_session_state()

    st.subheader("1. 資料來源")
    source_mode = st.radio(
        "資料來源", [SOURCE_GARMIN, SOURCE_LOCAL], index=0,
        horizontal=True, label_visibility="collapsed",
    )
    input_path_str = ""
    garmin: dict = {}
    if source_mode == SOURCE_LOCAL:
        input_path_str = _render_local_source()
    else:
        garmin = _render_garmin_source()

    st.subheader("2. 輸出位置")
    settings = _render_output_and_advanced(source_mode)

    st.markdown("")
    run_btn = st.button(
        "開始產生 AI 文字檔", type="primary", use_container_width=True
    )
    if run_btn:
        if source_mode == SOURCE_LOCAL:
            _run_local(input_path_str, settings)
        else:
            _run_garmin(garmin, settings)

    _render_import_result()
    _render_run_result()
    _scrub_passwords(source_mode)


if __name__ == "__main__":
    main()
