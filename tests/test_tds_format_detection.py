import os

from app.converters.tds_detector import detect_tds_format

NEW_DIR = "examples/tds/New"
OLD_DIR = "examples/tds/Old"


def _csvs(d):
    return [
        os.path.join(d, f)
        for f in os.listdir(d)
        if f.lower().endswith(".csv") and not f.startswith("~$")
    ]


def test_all_new_samples_detected_as_new():
    files = _csvs(NEW_DIR)
    assert files, "no New samples found"
    for f in files:
        assert detect_tds_format(f) == "new", f


def test_all_old_samples_detected_as_old():
    files = _csvs(OLD_DIR)
    assert files, "no Old samples found"
    for f in files:
        assert detect_tds_format(f) == "old", f
