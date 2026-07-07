"""Streamlit UI for Garmin TCX AI Local Processing."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from garmin_tcx_ai.pipeline import BundleRunConfig, run_bundle
from garmin_tcx_ai.ui_helpers import (
    default_output_dir,
    output_file_status,
    read_text_if_exists,
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

    # Initialize stable default output folder in session state
    if "default_output" not in st.session_state:
        st.session_state.default_output = str(default_output_dir())

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("參數設定")

        input_path_str = st.text_input(
            "Input path (TCX 檔案或資料夾路徑)",
            value="",
            help="指定單一 .tcx 檔案路徑，或包含 .tcx 檔案的資料夾路徑。",
        )

        output_dir_str = st.text_input(
            "Output folder (輸出資料夾)",
            value=st.session_state.default_output,
            help="轉換後的結果儲存目錄。",
        )

        gps_policy = st.selectbox(
            "GPS Policy (GPS 隱私政策)",
            options=["redact_start_end", "remove", "keep"],
            index=0,
            help="模糊化起終點、完全移除座標或保留原始座標。",
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

        st.markdown("**輸出選項**")
        write_coach_handoff = st.checkbox(
            "Generate coach handoff (產生 coach_handoff.md)",
            value=True,
        )
        write_atomic = st.checkbox(
            "Generate atomic artifacts (產生詳細除錯檔)",
            value=False,
        )

        st.markdown("<div style='margin-top: 1.5rem;'></div>",
                    unsafe_allow_html=True)
        run_btn = st.button("開始轉換")

        if run_btn:
            if not input_path_str.strip():
                st.error("錯誤：請填寫 Input path。")
            else:
                config = BundleRunConfig(
                    input_path=Path(input_path_str.strip()),
                    output_dir=Path(output_dir_str.strip()),
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
        st.subheader("轉換結果與預覽")

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

                st.markdown("---")

                # Markdown preview expanders
                sb_content = read_text_if_exists(
                    res.session_bundle_markdown_path
                )
                with st.expander("預覽 session_bundle.md", expanded=True):
                    if sb_content:
                        st.markdown(sb_content)
                    else:
                        st.write("未產生")

                ch_content = read_text_if_exists(
                    res.coach_handoff_markdown_path
                )
                with st.expander("預覽 coach_handoff.md", expanded=True):
                    if ch_content:
                        st.markdown(ch_content)
                    else:
                        st.write("未產生")
            else:
                st.error("❌ 轉換失敗！")
                st.markdown(f"**詳細錯誤**：\n```\n{res.error_message}\n```")
                if res.warning_messages:
                    st.warning("警告：")
                    for warning in res.warning_messages:
                        st.write(f"- {warning}")
        else:
            st.info("尚未執行轉換。請設定左側參數，並點擊「開始轉換」按鈕。")


if __name__ == "__main__":
    main()
