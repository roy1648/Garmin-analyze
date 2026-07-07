"""Tests for the coach handoff Markdown exporter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from garmin_tcx_ai.handoff import (
    render_coach_handoff_markdown,
    write_coach_handoff_markdown,
)
from garmin_tcx_ai.models import (
    Activity,
    Lap,
    ParsedActivity,
    PrivacyInfo,
    SourceInfo,
    Trackpoint,
)
from garmin_tcx_ai.session import build_session_bundle


def _activity(name: str, start: datetime | None) -> ParsedActivity:
    """Build one synthetic normalized activity."""
    trackpoint = Trackpoint(
        timestamp=start,
        latitude=25.0330,
        longitude=121.5654,
        distance_meters=0.0,
        heart_rate_bpm=150,
        run_cadence_spm=90,
        power_watts=250,
    )
    return ParsedActivity(
        source=SourceInfo("tcx", name, f"data/raw/{name}"),
        privacy=PrivacyInfo("redact_start_end"),
        activity=Activity(
            sport="Running",
            activity_id=start.isoformat() if start else name,
            start_time=start,
            total_time_seconds=600.0,
            distance_meters=5000.0,
            average_heart_rate_bpm=150,
            maximum_heart_rate_bpm=170,
        ),
        laps=[
            Lap(
                lap_index=1,
                start_time=start,
                total_time_seconds=600.0,
                distance_meters=5000.0,
                average_heart_rate_bpm=150,
                maximum_heart_rate_bpm=170,
            )
        ],
        trackpoints=[trackpoint],
    )


def test_render_coach_handoff_markdown() -> None:
    """Test rendering of the coach handoff Markdown report."""
    start = datetime(2026, 7, 5, 6, 0, tzinfo=timezone.utc)
    activities = [_activity("test.tcx", start)]
    bundle = build_session_bundle(
        activities,
        max_gap_minutes=30,
        timezone_name="Asia/Taipei",
    )

    md = render_coach_handoff_markdown(bundle)

    # 1. Check title and instruction
    assert "# TCX 教練交接報告" in md
    assert "這是多活動報告，每個 TCX 活動在報告中皆保持獨立紀錄；不代表多個 TCX 被合併成一堂訓練。" in md

    # 2. Check manual context empty fields
    assert "- 預定課表：" in md
    assert "- RPE：" in md
    assert "- 跑前疼痛：" in md
    assert "- 跑中疼痛：" in md
    assert "- 跑後疼痛：" in md
    assert "- 隔日狀態：" in md
    assert "- 補充說明：" in md

    # 3. Check that it contains session bundle content
    assert "# TCX 多活動報告" in md
    assert "## 資料政策" in md
    assert "## 輸出範圍" in md
    assert "## Session Candidate 候選分組" in md

    # 4. Check safety rules (no GPS, no interpretations/coaching advice)
    assert "latitude" not in md
    assert "longitude" not in md
    assert "suggested_questions" not in md
    assert "coaching_advice" not in md
    assert "medical_interpretation" not in md
    assert "Suggested Questions" not in md


def test_write_coach_handoff_markdown(tmp_path: Path) -> None:
    """Test writing the coach handoff Markdown file to the output directory."""
    start = datetime(2026, 7, 5, 6, 0, tzinfo=timezone.utc)
    activities = [_activity("test.tcx", start)]

    written_path = write_coach_handoff_markdown(
        activities,
        tmp_path,
        max_gap_minutes=30,
        timezone_name="Asia/Taipei",
    )

    expected_path = tmp_path / "session_bundle" / "coach_handoff.md"
    assert written_path == expected_path
    assert expected_path.is_file()

    content = expected_path.read_text(encoding="utf-8")
    assert "# TCX 教練交接報告" in content
