"""Streamlit UI for Garmin TCX AI Local Processing."""

from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from garmin_tcx_ai.pipeline import BundleRunConfig, run_bundle
from garmin_tcx_ai.ui_helpers import (
    default_output_dir,
    inspect_input_path,
    normalize_output_path,
    open_folder,
    output_file_status,
    read_output_text,
    select_file_dialog,
    select_folder_dialog,
)


def render_copy_button(label: str, text: str, key: str) -> None:
    """Render a browser-side copy-to-clipboard button.

    Args:
        label: The label for the button.
        text: The text to be copied to the clipboard.
        key: A unique key identifier for HTML elements.
    """
    if not text:
        st.caption("無可複製內容。")
        return

    safe_label = html.escape(label)
    text_json = json.dumps(text)
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
                status.textContent = "複製失敗，請手動選取文字。";
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


def main() -> None:
    """Run the Streamlit Local UI application."""
    st.set_page_config(
        page_title="Garmin TCX AI Local UI",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Inject premium UI aesthetics via custom CSS
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

    # Initialize stable default values in session state
    if "default_output" not in st.session_state:
        st.session_state.default_output = str(default_output_dir())
    if "input_path_val" not in st.session_state:
        st.session_state.input_path_val = ""
    if "output_path_val" not in st.session_state:
        st.session_state.output_path_val = st.session_state.default_output

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("參數設定")

        # Basic Section with native dialog pickers inline
        col_in_text, col_in_btn_file, col_in_btn_dir = st.columns(
            [3, 1, 1], vertical_alignment="bottom"
        )
        with col_in_text:
            input_path_str = st.text_input(
                "Input path (TCX 檔案或資料夾路徑)",
                value=st.session_state.input_path_val,
                help="指定單一 .tcx 檔案路徑，或包含 .tcx 檔案的資料夾路徑。",
            )
            st.session_state.input_path_val = input_path_str
        with col_in_btn_file:
            if st.button("選擇檔案", key="btn_select_file"):
                selected = select_file_dialog()
                if selected:
                    st.session_state.input_path_val = selected
                    st.rerun()
        with col_in_btn_dir:
            if st.button("選擇資料夾", key="btn_select_dir_in"):
                selected = select_folder_dialog()
                if selected:
                    st.session_state.input_path_val = selected
                    st.rerun()

        # Immediate input path check
        status = inspect_input_path(input_path_str)
        if status.is_valid:
            st.success(status.message)
        else:
            if not input_path_str.strip():
                st.warning(status.message)
            else:
                st.error(status.message)

        col_out_text, col_out_btn = st.columns(
            [4, 1], vertical_alignment="bottom"
        )
        with col_out_text:
            output_dir_str = st.text_input(
                "Output folder (輸出資料夾)",
                value=st.session_state.output_path_val,
                help="轉換後的結果儲存目錄。留空將使用自動產生的預設資料夾。",
            )
            st.session_state.output_path_val = output_dir_str
        with col_out_btn:
            if st.button("選擇資料夾", key="btn_select_dir_out"):
                selected = select_folder_dialog()
                if selected:
                    st.session_state.output_path_val = selected
                    st.rerun()

        if st.button("重新產生預設輸出資料夾"):
            st.session_state.default_output = str(default_output_dir())
            st.session_state.output_path_val = st.session_state.default_output
            st.rerun()

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
        tcx_desc = f"{status.tcx_count} 個" if status.is_valid else "無效"
        st.markdown(
            f"- **Input**: `{input_path_str.strip() or '未填寫'}`\n"
            f"- **TCX count**: {tcx_desc}\n"
            f"- **Output**: `{output_dir_str.strip() or '將使用預設路徑'}`\n"
            f"- **GPS policy**: `{gps_policy}`\n"
            f"- **Coach handoff**: {'on' if write_coach_handoff else 'off'}\n"
            f"- **Atomic artifacts**: {'on' if write_atomic else 'off'}"
        )

        if gps_policy == "keep":
            st.warning(
                "目前 GPS policy = keep，輸出可能保留完整座標。請確認你真的需要保留 GPS。"
            )

        st.markdown(
            "<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True
        )
        run_btn = st.button("開始轉換")

        if run_btn:
            status = inspect_input_path(input_path_str)
            if not status.is_valid:
                st.error(f"無法執行：{status.message}")
                if "run_result" in st.session_state:
                    del st.session_state["run_result"]
            else:
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
                st.session_state.run_result = result

    with col2:
        st.subheader("轉換結果")

        if "run_result" in st.session_state:
            res = st.session_state.run_result
            if res.success:
                st.success("🎉 轉換成功！")

                if res.warning_messages:
                    st.warning("執行過程中包含以下警告：")
                    for warning in res.warning_messages:
                        st.write(f"- {warning}")

                # Display key metrics
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

                # Check and read session_bundle.json
                sb_json_text = read_output_text(res.session_bundle_json_path)
                if sb_json_text:
                    render_copy_button(
                        "複製 session_bundle.json",
                        sb_json_text,
                        "session_bundle_json",
                    )
                else:
                    st.write("session_bundle.json: 未產生，無法複製。")

                # Check and read session_bundle.md
                sb_md_text = read_output_text(res.session_bundle_markdown_path)
                if sb_md_text:
                    render_copy_button(
                        "複製 session_bundle.md",
                        sb_md_text,
                        "session_bundle_markdown",
                    )
                else:
                    st.write("session_bundle.md: 未產生，無法複製。")

                # Check and read coach_handoff.md
                ch_md_text = read_output_text(res.coach_handoff_markdown_path)
                if ch_md_text:
                    render_copy_button(
                        "複製 coach_handoff.md",
                        ch_md_text,
                        "coach_handoff_markdown",
                    )
                else:
                    st.write("coach_handoff.md: 未產生，無法複製。")
            else:
                st.error("❌ 轉換失敗！")
                st.error(
                    "轉換失敗，請先檢查 Input path、TCX 檔案格式、Timezone 或輸出路徑。"
                )
                with st.expander("技術錯誤訊息", expanded=True):
                    st.code(
                        res.error_message or "無詳細錯誤訊息", language="text"
                    )
                if res.warning_messages:
                    st.warning("警告：")
                    for warning in res.warning_messages:
                        st.write(f"- {warning}")
        else:
            st.info("尚未執行轉換。請設定左側參數，並點擊「開始轉換」按鈕。")

    # Render preview section at the bottom, using full width and unrestricted height
    if "run_result" in st.session_state:
        res = st.session_state.run_result
        if res.success:
            st.markdown("---")
            st.markdown("### 輸出檔案預覽")

            sb_md_text = read_output_text(res.session_bundle_markdown_path)
            ch_md_text = read_output_text(res.coach_handoff_markdown_path)

            tab1, tab2 = st.tabs(["session_bundle.md", "coach_handoff.md"])
            with tab1:
                if sb_md_text:
                    st.markdown(sb_md_text)
                else:
                    st.write("未產生")
            with tab2:
                if ch_md_text:
                    st.markdown(ch_md_text)
                else:
                    st.write("未產生")


if __name__ == "__main__":
    main()
