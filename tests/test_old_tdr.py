"""Files written by VStim < 1.42 (2004-2006 recordings): $FH1 v2 (no .ini line), $TH1 with
the layout of v2 but version written as 1, $TS1 v1 (no performance counter, 32 triggers),
no $TS2-$TS4. old_v2.tdr is the head of Original/.../daq_2005_01_06/2005_01_06.tdr."""
import datetime
import pathlib

import vstim.tdr as tdr

OLD = pathlib.Path(__file__).parent / "old_v2.tdr"


def test_FileStartHeader_v2_and_v1():
    h = tdr.FileStartHeader.from_lines(
        [
            "$FH1   4   2",
            "1.3\t\t// VStim program version",
            "1.01\t\t// .tdr file format version",
            "06.01.2005\t09:41:07\t100\t// date, start time, refresh rate",
        ]
    )
    assert h.headerVersion == 2 and h.nLines == 4
    assert h.vstimVersion == "1.3" and h.tdrVersion == "1.01"
    assert h.date == datetime.date(2005, 1, 6)
    assert h.startTime == datetime.time(9, 41, 7)
    assert h.refreshRate == 100.0 and h.iniFile is None

    h1 = tdr.FileStartHeader.from_lines(
        ["$FH1   4   1", "1.2", "1.01", "07.07.2002\t20:14:34"]
    )
    assert h1.refreshRate is None and h1.iniFile is None


def test_TrialHeader_v1_layout_9_tokens():
    lines = [
        "$TH1   2   1    12    5    1    1    1    710.00",
        "$TS1   1   1    12  09:41:18    0.0000  2.8000" + "  -0.0100" * 62,
    ]
    h = tdr.TrialHeader.from_lines(lines)
    assert h.trialNumber == 12 and h.stimulusNumber == 5 and h.timeSequence == 1
    assert h.outcome == tdr.TrialOutcome.Hit
    assert h.manipulandum == tdr.Manipulandum.ReleaseLever1
    assert h.reactionTimeMS == 710.0
    assert h.wasHit is None and h.eyeControlFlag is None and h.rewardDurationMS is None
    assert h.subheader1.trialNumber == 12
    assert h.subheader2 is None and h.subheader3 is None and h.subheader4 is None


def test_TrialHeader_v3_and_v4_layouts():
    v3 = tdr.TrialHeader.from_lines(
        ["$TH1   2   1    368    5    3    1    1    452.8   1   4   5.7900"]
    )
    assert v3.eyeControlFlag is True and v3.intervalOfFrameLoss == 4
    assert v3.timeOfFrameLoss == 5.79 and v3.lastInterval is None
    v4 = tdr.TrialHeader.from_lines(
        ["$TH1   2   4    368    5    3    1    1    452.8   6   1   4   5.7900"]
    )
    assert v4.lastInterval == 6 and v4.eyeControlFlag is True
    assert v4.intervalOfFrameLoss == 4 and v4.timeOfFrameLoss == 5.79


def test_TrialSubheader1_v1_has_32_triggers_and_no_performance_counter():
    line = "$TS1   1   1    11  09:41:13    0.0000  2.8000   2.8000  3.2300" + "  -0.0100" * 60
    sh = tdr.TrialSubheader1.from_lines([line])
    assert sh.headerVersion == 1 and sh.trialNumber == 11
    assert sh.tAbsTrialStart == "09:41:13" and sh.tRelTrialStartMIN is None
    assert len(sh.tPositiveTriggerTransitionMS) == 32
    assert len(sh.tNegativeTriggerTransitionMS) == 32
    assert sh.tPositiveTriggerTransitionMS[1] == 2800.0


def test_read_old_file():
    f = tdr.read_tdr(OLD)
    assert isinstance(f.headers[0], tdr.FileStartHeader)
    trials = f.get_trials()
    assert [t.trialNumber for t in trials] == [11, 12, 13]
    assert trials[0].outcome == tdr.TrialOutcome.EyeErr
    assert trials[1].outcome == tdr.TrialOutcome.Hit
    assert trials[0].tClockStartS == 6  # 09:41:13 - 09:41:07
    assert trials[0].get_interval_durations()[:3] == [2800.0, 430.0, 1010.0]
    assert trials[0].get_trial_duration_after_start_signal() is None  # no $TS3
    assert len(trials[0].stimulusObjects) > 20


def test_FileEndHeader_and_session_metadata():
    h2 = tdr.FileEndHeader.from_lines(
        [
            "$FH2 3 1",
            "2023-06-09 10:24:09  // end of recording",
            "//  <nAll> <nDone> ...",
            "3 3 0 0 0 0 0 3 0 0 0",
        ]
    )
    assert h2.endTime == datetime.datetime(2023, 6, 9, 10, 24, 9)
    assert h2.counts == [3, 3, 0, 0, 0, 0, 0, 3, 0, 0, 0]
    h3 = tdr.SessionMetadataHeader.from_lines(['$FH3 1 1 {"metadataVersion":1,"x":"a//b"}'])
    assert h3.metadata == {"metadataVersion": 1, "x": "a//b"}
