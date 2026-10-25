import pathlib
import zipfile

import pytest

from vstim import ini

DATA = pathlib.Path(__file__).parent


@pytest.fixture
def v1_ini(tmp_path):
    """Stimulus definition of VStim 1.x (.ini file version 5, 2002)."""
    with zipfile.ZipFile(DATA / "test_v1.ini.zip") as archive:
        archive.extractall(tmp_path)
    return tmp_path / "test_v1.ini"


def test_read_version_5(v1_ini):
    assert ini.check_version(v1_ini) == 5
    stim = ini.read(v1_ini)
    assert stim.n_stimuli > 0 and len(stim.presentations) == stim.n_stimuli
    assert stim.time_sequences and all(seq.intervals for seq in stim.time_sequences)
    assert stim.objects and stim.objects[0].type
    assert set(stim.stimuli_used()) <= set(stim.presentations)


def test_vstim_2_files_are_rejected(tmp_path):
    path = tmp_path / "v2.ini"
    path.write_text(
        "      63  /* VERSION; (.ini file version number)\r\n"
        "       2  /* PROG VERS MAJOR; (program version number)\r\n"
        "      55  /* PROG VERS MINOR; (program version number)\r\n",
        encoding="latin-1",
    )
    with pytest.raises(ini.UnsupportedIniVersion, match="VStim 2.55"):
        ini.read(path)


@pytest.mark.parametrize("version", [1, 3, 6])
def test_other_versions_are_rejected(tmp_path, version):
    path = tmp_path / "old.ini"
    path.write_text(f"       {version}  /* VERSION; (.ini file version number)\r\nOBJECT LIST START\r\n", encoding="latin-1")
    with pytest.raises(ini.UnsupportedIniVersion, match=f"version {version}"):
        ini.read(path)


def test_parse_stim_list():
    assert ini.parse_stim_list("1, 2, 5:7,") == {1, 2, 5, 6, 7}
