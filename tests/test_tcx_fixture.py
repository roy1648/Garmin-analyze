"""Smoke tests for the committed sanitized TCX fixture."""

from pathlib import Path
from xml.etree import ElementTree

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "minimal_running.tcx"
TCX_NAMESPACE = (
    "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
)
ACTIVITY_EXTENSION_NAMESPACE = (
    "http://www.garmin.com/xmlschemas/ActivityExtension/v2"
)
NAMESPACES = {
    "tcx": TCX_NAMESPACE,
    "ns3": ACTIVITY_EXTENSION_NAMESPACE,
}
SYNTHETIC_ACTIVITY_ID = "2000-01-01T00:00:00Z"


def test_minimal_running_fixture_is_valid_and_stable() -> None:
    """The sanitized fixture keeps its expected representative structure."""
    root = ElementTree.parse(FIXTURE_PATH).getroot()

    assert root.tag == f"{{{TCX_NAMESPACE}}}TrainingCenterDatabase"

    activities = root.findall(".//tcx:Activity", NAMESPACES)
    laps = root.findall(".//tcx:Lap", NAMESPACES)
    trackpoints = root.findall(".//tcx:Trackpoint", NAMESPACES)

    assert len(activities) == 1
    assert activities[0].get("Sport") == "Running"
    assert len(laps) == 1
    assert len(trackpoints) == 2
    assert activities[0].findtext("tcx:Id", namespaces=NAMESPACES) == (
        SYNTHETIC_ACTIVITY_ID
    )


def test_minimal_running_fixture_has_representative_extensions() -> None:
    """The fixture includes known Garmin extension elements."""
    root = ElementTree.parse(FIXTURE_PATH).getroot()

    assert root.find(".//tcx:Extensions", NAMESPACES) is not None
    assert root.find(".//ns3:Speed", NAMESPACES) is not None
    assert root.find(".//ns3:RunCadence", NAMESPACES) is not None
    assert root.find(".//ns3:Watts", NAMESPACES) is not None


def test_minimal_running_fixture_excludes_creator_identity() -> None:
    """The sanitized fixture excludes creator and device identity nodes."""
    root = ElementTree.parse(FIXTURE_PATH).getroot()

    assert root.find(".//tcx:Creator", NAMESPACES) is None
    assert root.find(".//tcx:Author", NAMESPACES) is None
    assert root.find(".//tcx:UnitId", NAMESPACES) is None
    assert root.find(".//tcx:ProductID", NAMESPACES) is None
