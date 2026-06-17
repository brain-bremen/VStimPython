import csv
import pathlib

import pytest

from vstim.tdr_to_csv import convert, main


TEST_TDR = pathlib.Path(__file__).parent / "test.tdr"


def read_csv(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def test_convert_creates_csv(tmp_path):
    out = tmp_path / "output.csv"
    convert(TEST_TDR, out)
    assert out.exists()


def test_convert_columns(tmp_path):
    out = tmp_path / "output.csv"
    convert(TEST_TDR, out)
    rows = read_csv(out)
    assert rows[0].keys() == {"trialno", "trialtype", "outcome", "reactionTimeMS", "trialStartS", "trialEndS"}


def test_convert_row_count(tmp_path):
    out = tmp_path / "output.csv"
    convert(TEST_TDR, out)
    rows = read_csv(out)
    assert len(rows) == 5


def test_convert_first_row_values(tmp_path):
    out = tmp_path / "output.csv"
    convert(TEST_TDR, out)
    row = read_csv(out)[0]
    assert int(row["trialno"]) == 1
    assert int(row["trialtype"]) == 0
    assert row["outcome"] == "Hit"
    assert float(row["reactionTimeMS"]) == pytest.approx(420.0)
    assert float(row["trialStartS"]) == pytest.approx(60.0915, rel=1e-4)
    assert float(row["trialEndS"]) > float(row["trialStartS"])


def test_main_default_output_path(tmp_path, monkeypatch):
    tdr_copy = tmp_path / "test.tdr"
    tdr_copy.write_bytes(TEST_TDR.read_bytes())
    monkeypatch.setattr("sys.argv", ["tdr-to-csv", str(tdr_copy)])
    main()
    assert (tmp_path / "test.csv").exists()


def test_main_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["tdr-to-csv", str(tmp_path / "nonexistent.tdr")])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
