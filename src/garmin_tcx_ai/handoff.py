"""Module to generate the coach handoff Markdown file."""

from __future__ import annotations

from pathlib import Path

from garmin_tcx_ai.models import ParsedActivity
from garmin_tcx_ai.session import (
    build_session_bundle,
    render_session_bundle_markdown,
)


def render_coach_handoff_markdown(bundle: dict) -> str:
    """Render a Markdown coach handoff report from a session bundle dict.

    Args:
        bundle: The session bundle dictionary.

    Returns:
        The rendered Markdown string.
    """
    sb_md = render_session_bundle_markdown(bundle)

    lines = [
        "# TCX 教練交接報告",
        "",
        "這是多活動報告，每個 TCX 活動在報告中皆保持獨立紀錄；不代表多個 TCX 被合併成一堂訓練。",
        "",
        "## 手動補充資訊",
        "",
        "- 預定課表：",
        "- RPE：",
        "- 跑前疼痛：",
        "- 跑中疼痛：",
        "- 跑後疼痛：",
        "- 隔日狀態：",
        "- 補充說明：",
        "",
        "---",
        "",
        sb_md,
    ]
    return "\n".join(lines)


def write_coach_handoff_markdown(
    activities: list[ParsedActivity],
    output_dir: Path,
    max_gap_minutes: int = 30,
    timezone_name: str = "Asia/Taipei",
) -> Path:
    """Write coach_handoff.md for multiple normalized activities.

    Args:
        activities: A list of parsed activities.
        output_dir: The directory where the session_bundle folder will be
            created and the handoff markdown file will be written.
        max_gap_minutes: The maximum gap in minutes between trackpoints.
        timezone_name: The timezone name to use for local dates/times.

    Returns:
        The path to the written file.
    """
    folder = Path(output_dir) / "session_bundle"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "coach_handoff.md"
    bundle = build_session_bundle(
        activities,
        max_gap_minutes,
        timezone_name,
    )
    content = render_coach_handoff_markdown(bundle)
    target.write_text(content, encoding="utf-8", newline="\n")
    return target
