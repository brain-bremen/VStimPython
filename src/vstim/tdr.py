from enum import Enum
import pathlib
import abc
import warnings
from dataclasses import dataclass, field
import datetime

nIntervals = 20


def remove_comment(line: str):
    return line.split(sep="//", maxsplit=1)[0].rstrip()


class HeaderId(Enum):
    FH1 = "$FH1"
    FH2 = "$FH2"
    FH3 = "$FH3"
    TH1 = "$TH1"
    TS1 = "$TS1"
    TS2 = "$TS2"
    TS3 = "$TS3"
    TS4 = "$TS4"
    OH1 = "$OH1"
    OS1 = "$OS1"
    UNKNOWN = "$UNKNOWN"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


@dataclass(kw_only=True)
class Header(abc.ABC):
    id: HeaderId
    headerVersion: int
    nLines: int

    @staticmethod
    @abc.abstractmethod
    def from_lines(lines: list[str]):
        pass


@dataclass(kw_only=True)
class FileStartHeader(Header):
    id: HeaderId = HeaderId.FH1
    nLines: int = 5
    headerVersion: int = 3
    vstimVersion: str = None
    tdrVersion: str = None
    date: datetime.date = None
    startTime: datetime.time = None
    refreshRate: float = None
    iniFile: str = None

    @staticmethod
    def from_lines(lines: list[str]):
        """Versions 1 and 2 (VStim <= 1.41, e.g. the 2004-2006 recordings) have no .ini
        line; version 1 also has no refresh rate; nLines counts the header line itself."""
        new = FileStartHeader()
        # line 1
        id, nLines, version = lines[0].split()[:3]
        assert new.id.value == id
        new.nLines = int(nLines)
        new.headerVersion = int(version)
        assert new.headerVersion in (1, 2, 3), f"unsupported $FH1 version {version}"

        # line 2
        new.vstimVersion = remove_comment(lines[1]).strip()

        # line 3
        new.tdrVersion = remove_comment(lines[2]).strip()

        # line 4
        tokens = remove_comment(lines[3]).split()
        new.date = datetime.datetime.strptime(tokens[0], "%d.%m.%Y").date()
        new.startTime = datetime.datetime.strptime(tokens[1], "%H:%M:%S").time()
        new.refreshRate = float(tokens[2]) if len(tokens) > 2 else None

        # line 5 (version 3 only)
        if new.headerVersion >= 3:
            new.iniFile = remove_comment(lines[4])
        return new


@dataclass(kw_only=True)
class FileEndHeader(Header):
    """$FH2 (since TDR 1.12): end time and trial counts. Count order as documented:
    nAll nDone nNotStartedErr nEyeErr nEarlyErr nEarlyHit nEarlyWrongRespErr nHit
    nWrongRespErr nLateErr nInexpStartErr nWrongStartErr nFrameLossErr (older files may
    have fewer entries)."""

    id: HeaderId = HeaderId.FH2
    nLines: int = 3
    headerVersion: int = 1
    endTime: datetime.datetime = None
    counts: list[int] = None

    @staticmethod
    def from_lines(lines: list[str]):
        id, nLines, version = lines[0].split()[:3]
        new = FileEndHeader(nLines=int(nLines), headerVersion=int(version))
        new.endTime = datetime.datetime.strptime(
            remove_comment(lines[1]).strip(), "%Y-%m-%d %H:%M:%S"
        )
        data = [remove_comment(l).split() for l in lines[2:] if not l.startswith("//")]
        new.counts = [int(t) for t in data[0]] if data and data[0] else []
        return new


@dataclass(kw_only=True)
class SessionMetadataHeader(Header):
    """$FH3 (since TDR 1.18): one line of JSON session metadata after the identifier."""

    id: HeaderId = HeaderId.FH3
    nLines: int = 1
    headerVersion: int = 1
    metadata: dict = None

    @staticmethod
    def from_lines(lines: list[str]):
        import json

        id, nLines, version, payload = lines[0].split(None, 3)
        return SessionMetadataHeader(
            nLines=int(nLines), headerVersion=int(version), metadata=json.loads(payload)
        )


class TrialOutcome(Enum):
    """Trial result codes (VStim ``VStimLib/TDR.h``)."""

    Undetermined = -1
    NotStarted = 0
    Hit = 1
    WrongResponse = 2
    EarlyHit = 3
    EarlyWrongResponse = 4
    Early = 5
    Late = 6
    EyeErr = 7
    InexpectedStartSignal = 8
    WrongStartSignal = 9
    Cancelled = 10  # since VStim 2.50

    @classmethod
    def _missing_(cls, value):
        """Codes of newer VStim versions: keep the value instead of failing to read the file."""
        if not isinstance(value, int):
            return None
        warnings.warn(f"Unknown trial outcome code {value}", category=UserWarning)
        member = object.__new__(cls)
        member._name_ = f"Unknown{value}"
        member._value_ = value
        return member


class Manipulandum(Enum):
    NoManipulandum = 0
    PressLever1 = -1
    ReleaseLever1 = 1
    PressLever2 = -2
    ReleaseLever2 = 2
    PressLever3 = -3
    ReleaseLever3 = 3
    EyeResponseField0 = 11
    EyeResponseField1 = 12
    EyeResponseField2 = 13
    EyeResponseField3 = 14
    EyeResponseField4 = 15
    EyeResponseField5 = 16
    EyeResponseField6 = 17
    EyeResponseField7 = 18
    EyeResponseField8 = 19


class StartResponseSignalCode(Enum):
    PressLever1 = -1
    ReleaseLever1 = 1
    PressLever2 = -2
    ReleaseLever2 = 2
    PressLever3 = -3
    ReleaseLever3 = 3
    LookRF1 = 11
    LookRF2 = 12
    LookRF3 = 13
    LookRF4 = 14
    LookRF5 = 15
    LookRF6 = 16
    LookRF7 = 17
    LookRF8 = 18
    StartFixating = 20
    IsFixating = 21


class IntervalType(Enum):
    Normal = 0
    WaitForStartSignal = 1
    ResponseAllowed = 2
    ResponseRequired = 3


@dataclass(kw_only=True)
class TrialSubheader1(Header):
    id: HeaderId = HeaderId.TS1
    nLines: int = 1
    headerVersion: int = 3
    trialNumber: int = None
    tAbsTrialStart: str = None
    tRelTrialStartMIN: float = None
    tPositiveTriggerTransitionMS: list[float] = None
    tNegativeTriggerTransitionMS: list[float] = None

    @staticmethod
    def from_lines(lines: list[str]):
        new = TrialSubheader1()
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]

        assert new.id.value == id
        assert new.nLines == int(nLines)

        new.headerVersion = int(version)
        new.trialNumber = int(tokens[3])
        new.tAbsTrialStart = tokens[4]
        # version 3 (VStim >= 1.42) adds the performance-counter time in 0.1 ms ticks;
        # versions 1/2 have only the clock time (1 s resolution)
        first = 5
        if new.headerVersion >= 3:
            new.tRelTrialStartMIN = float(tokens[5]) / 60.0 / 10000.0
            first = 6

        # version 1: 32 virtual trigger lines, version >= 2: 48 (number follows from the line length)
        new.tPositiveTriggerTransitionMS = [float(t) * 1000 for t in tokens[first::2]]
        new.tNegativeTriggerTransitionMS = [float(t) * 1000 for t in tokens[first + 1 :: 2]]
        return new


@dataclass(kw_only=True)
class TrialSubheader2(Header):
    id: HeaderId = HeaderId.TS2
    nLines: int = 1
    headerVersion: int = 1
    tIntendedIntervalDurationMS: list[float] = None

    @staticmethod
    def from_lines(lines: list[str]):
        new = TrialSubheader2()
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]

        assert new.id.value == id
        assert new.nLines == int(nLines)
        assert new.headerVersion == int(version)

        new.tIntendedIntervalDurationMS = [float(t) * 1000 for t in tokens[3:]]
        return new


@dataclass(kw_only=True)
class TrialSubheader3(Header):
    id: HeaderId = HeaderId.TS3
    nLines: int = 1
    headerVersion: int = 1
    intervalType: list[IntervalType]

    @staticmethod
    def from_lines(lines: list[str]):
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]

        assert TrialSubheader3.id.value == id
        assert TrialSubheader3.nLines == int(nLines)
        assert TrialSubheader3.headerVersion == int(version)

        new = TrialSubheader3(
            intervalType=[IntervalType(int(code)) for code in tokens[3:]]
        )
        return new


@dataclass(kw_only=True)
class TrialSubheader4(Header):
    id: HeaderId = HeaderId.TS4
    nLines: int = 1
    headerVersion: int = 1
    signals: list[StartResponseSignalCode] = None

    @dataclass
    class StartStopSignal:
        type: StartResponseSignalCode
        # interval of occurrence
        interval: int
        # time of occurrence relative to begin of interval
        tOccurrenceMS: float

    @staticmethod
    def from_lines(lines: list[str]):
        new = TrialSubheader4()
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]

        assert new.id.value == id
        assert new.nLines == int(nLines)
        assert new.headerVersion == int(version)

        nSignals = int(tokens[3])

        new.signals = []
        for iSignal in range(nSignals):
            type = StartResponseSignalCode(int(tokens[4 + iSignal * 3]))
            interval = int(tokens[5 + iSignal * 3])
            tOccurrenceMS = float(tokens[6 + iSignal * 3])
            new.signals.append(
                TrialSubheader4.StartStopSignal(type, interval, tOccurrenceMS)
            )

        return new


@dataclass(kw_only=True)
class TrialHeader(Header):

    id: HeaderId = HeaderId.TH1
    nLines: int = 5
    headerVersion: int = 6
    trialNumber: int = None
    stimulusNumber: int = None
    timeSequence: int = None
    wasPerfectMonkey: bool = None  # since $TH1 v5 (VStim 1.42)
    wasHit: bool = None  # since v5
    outcome: TrialOutcome = None
    manipulandum: Manipulandum = None
    wasPreciseFixation: bool = None  # since v5
    reactionTimeMS: float = None
    rewardDurationMS: float = None  # since v5
    lastInterval: int = None  # since v4 (VStim 1.40)
    eyeControlFlag: bool = None  # since v3 (VStim 1.38)
    intervalOfFrameLoss: int = None  # since v3
    timeOfFrameLoss: float = None  # since v3
    subheader1: TrialSubheader1 = None
    subheader2: TrialSubheader2 = None  # since VStim 1.42
    subheader3: TrialSubheader3 = None  # since VStim 1.42
    subheader4: TrialSubheader4 = None  # since VStim 1.46

    @staticmethod
    def from_lines(lines: list[str]):
        """Parse a $TH1 record. Before VStim 1.40 the version field was always written as 1
        even though the layout grew (see TDR change history), so the layout is detected from
        the number of tokens of the first line:

        =======  ===========================================================
        tokens   layout
        =======  ===========================================================
        9        v1/v2: trial, stim, timeSeq, result, manipulandum, RT
        12       v3: + eyeControl, intervalOfFrameLoss, timeOfFrameLoss
        13       v4: RT, terminatingInterval, eyeControl, itvFL, timeFL
        17       v5/v6: perfect, hit, result, manip, precise, RT, reward, ...
        =======  ===========================================================
        """
        tokens = lines[0].split()
        id, nLinesStr, version = tokens[0:3]

        assert HeaderId.TH1.value == id
        if len(tokens) >= 17:
            # v5/v6 (VStim >= 1.42): keep the class defaults (nLines=5, version=6), as before;
            # v5 reports 4 lines but has 5 (VStim bug #210, see read_tdr)
            new = TrialHeader()
        else:
            # older layouts: record what the file says (the version is unreliable, see above)
            new = TrialHeader(headerVersion=int(version), nLines=int(nLinesStr))
        new.trialNumber = int(tokens[3])
        new.stimulusNumber = int(tokens[4])
        new.timeSequence = int(tokens[5])
        n = len(tokens)
        if n >= 17:  # v5, v6
            new.wasPerfectMonkey = bool(int(tokens[6]))
            new.wasHit = bool(int(tokens[7]))
            new.outcome = TrialOutcome(int(tokens[8]))
            new.manipulandum = Manipulandum(int(tokens[9]))
            new.wasPreciseFixation = bool(int(tokens[10]))
            new.reactionTimeMS = float(tokens[11])
            new.rewardDurationMS = float(tokens[12])
            new.lastInterval = int(tokens[13])
            new.eyeControlFlag = bool(int(tokens[14]))
            new.intervalOfFrameLoss = int(tokens[15])
            new.timeOfFrameLoss = float(tokens[16])
        elif n in (9, 12, 13):  # v1/v2, v3, v4
            new.outcome = TrialOutcome(int(tokens[6]))
            new.manipulandum = Manipulandum(int(tokens[7]))
            new.reactionTimeMS = float(tokens[8])
            if n == 13:
                new.lastInterval = int(tokens[9])
                tokens = tokens[:9] + tokens[10:]
            if n >= 12:
                new.eyeControlFlag = bool(int(tokens[9]))
                new.intervalOfFrameLoss = int(tokens[10])
                new.timeOfFrameLoss = float(tokens[11])
        else:
            raise ValueError(f"unexpected $TH1 line with {n} tokens: {lines[0]!r}")

        # process subheaders
        lines = lines[1:]
        for iLine, line in enumerate(lines):
            if not line.startswith("$"):
                continue
            subheaderIdStr, nLinesStr, subheaderVersion = line.split()[:3]
            subheaderId = HeaderId(subheaderIdStr)
            if subheaderId not in SubHeaderIdMap.keys():
                continue
            nLines = int(nLinesStr)
            subheader = SubHeaderIdMap[subheaderId].from_lines(
                lines[iLine : iLine + nLines]
            )
            match subheaderId:
                case HeaderId.TS1:
                    new.subheader1 = subheader
                case HeaderId.TS2:
                    new.subheader2 = subheader
                case HeaderId.TS3:
                    new.subheader3 = subheader
                case HeaderId.TS4:
                    new.subheader4 = subheader

        return new


@dataclass(kw_only=True)
class ObjectHeader(Header):
    # // header / # of lines / version / object# / show-hide / Xpos / Ypos / Zpos / RotX / RotY / RotZ / ObjTypeName
    id: HeaderId = HeaderId.OH1
    nLines: int = None  # including subheader
    headerVersion: int = 1
    objectNumber: int = None
    show: bool = None
    xPos: float = None
    yPos: float = None
    zPos: float = None
    rotX: float = None
    rotY: float = None
    rotZ: float = None
    typeName: str = None
    subheaders: list[Header] = None

    @staticmethod
    def from_lines(lines: list[str]):
        new = ObjectHeader()
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]
        new.nLines = int(nLines)
        new.headerVersion = int(version)

        assert new.headerVersion == int(version)

        new.objectNumber = int(tokens[3])
        new.show = bool(int(tokens[4]))
        new.xPos = float(tokens[5])
        new.yPos = float(tokens[6])
        new.zPos = float(tokens[7])
        new.rotX = float(tokens[8])
        new.rotY = float(tokens[9])
        new.rotZ = float(tokens[10])
        new.typeName = " ".join(tokens[11:])

        # process subheaders
        lines = lines[1:]
        new.subheaders = []
        for iLine, line in enumerate(lines):
            if not line.startswith("$OS"):
                continue
            subheaderId, nLines, subheaderVersion = line.split()[:3]
            if not new.typeName in ObjectTypeNameMap.keys():
                continue
            nLines = int(nLines)
            subheader = ObjectTypeNameMap[new.typeName]()
            subheader.from_lines(lines[iLine : iLine + nLines])
            new.subheaders.append(subheader)

        return new


@dataclass(kw_only=True)
class FixationPoint1(Header):
    id: HeaderId = HeaderId.OS1
    nLines: int = 1
    headerVersion: int = 1
    isActive: bool = None
    tAppearanceMS: list[float] = None
    tDisappearanceMS: list[float] = None

    @staticmethod
    def from_lines(lines: list[str]) -> Header:
        new = FixationPoint1()
        tokens = lines[0].split()
        id, nLines, version = tokens[0:3]

        assert new.id.value == id
        assert new.nLines == int(nLines)
        assert new.headerVersion == int(version)

        new.isActive = bool(int(tokens[3]))
        new.tAppearanceMS = [float(t) * 1000 for t in tokens[4::2]]
        new.tDisappearanceMS = [float(t) * 1000 for t in tokens[5::2]]
        return new


ObjectTypeNameMap = {
    "Fixation Point 1": FixationPoint1,
}


HeaderIdMap: dict[HeaderId, type[Header]] = {
    HeaderId.FH1: FileStartHeader,
    HeaderId.FH2: FileEndHeader,
    HeaderId.FH3: SessionMetadataHeader,
    HeaderId.TH1: TrialHeader,
    HeaderId.OH1: ObjectHeader,
}
SubHeaderIdMap: dict[HeaderId, type[Header]] = {
    HeaderId.TS1: TrialSubheader1,
    HeaderId.TS2: TrialSubheader2,
    HeaderId.TS3: TrialSubheader3,
    HeaderId.TS4: TrialSubheader4,
}


@dataclass
class Trial:
    # from $TH1
    trialNumber: int = None
    stimulusNumber: int = None
    timeSequence: int = None
    wasPerfectMonkey: bool = None
    wasHit: bool = None
    outcome: TrialOutcome = None
    manipulandum: Manipulandum = None
    wasPreciseFixation: bool = None
    reactionTimeMS: float = None
    rewardDurationMS: float = None
    lastInterval: int = None
    eyeControlFlag: bool = None
    intervalOfFrameLoss: int = None
    timeOfFrameLoss: float = None

    # from $TS1
    tAbsTrialStart: str = None
    tRelTrialStartMIN: float = None
    tPositiveTriggerTransitionMS: list[float] = None
    tNegativeTriggerTransitionMS: list[float] = None

    # derived: seconds from the file start time ($FH1) to the trial start, from the wall
    # clock in $TS1 (1 s resolution; the only trial start time in files before VStim 1.42)
    tClockStartS: float = None

    # from $TS2
    tIntendedIntervalDurationMS: list[float] = None

    # from $TS3
    intervalType: IntervalType = None

    # from $TS4
    signals: list[TrialSubheader4.StartStopSignal] = None

    # from $OH1
    stimulusObjects: list[ObjectHeader] = field(default_factory=list)

    def from_trial_header(self, header: TrialHeader):
        self.trialNumber = header.trialNumber
        self.stimulusNumber = header.stimulusNumber
        self.timeSequence = header.timeSequence
        self.wasPerfectMonkey = header.wasPerfectMonkey
        self.wasHit = header.wasHit
        self.outcome = header.outcome
        self.manipulandum = header.manipulandum
        self.wasPreciseFixation = header.wasPreciseFixation
        self.reactionTimeMS = header.reactionTimeMS
        self.rewardDurationMS = header.rewardDurationMS
        self.lastInterval = header.lastInterval
        self.eyeControlFlag = header.eyeControlFlag
        self.intervalOfFrameLoss = header.intervalOfFrameLoss
        self.timeOfFrameLoss = header.timeOfFrameLoss

        sh1, sh2, sh3, sh4 = header.subheader1, header.subheader2, header.subheader3, header.subheader4
        if sh1 is not None:
            self.tAbsTrialStart = sh1.tAbsTrialStart
            self.tRelTrialStartMIN = sh1.tRelTrialStartMIN
            self.tPositiveTriggerTransitionMS = sh1.tPositiveTriggerTransitionMS
            self.tNegativeTriggerTransitionMS = sh1.tNegativeTriggerTransitionMS
        # $TS2-$TS4 do not exist in files written by VStim < 1.42 / 1.46
        if sh2 is not None:
            self.tIntendedIntervalDurationMS = sh2.tIntendedIntervalDurationMS
        if sh3 is not None:
            self.intervalType = sh3.intervalType
        if sh4 is not None:
            self.signals = sh4.signals

    def get_trial_duration(self) -> float:
        """Returns the total duration of the trial in milliseconds."""
        return sum(self.get_interval_durations())

    def get_trial_duration_after_start_signal(self) -> float | None:
        """Returns the duration of the trial from the end of the first interval waiting for a start signal in milliseconds."""
        if self.intervalType is None:  # no $TS3 in this file
            return None
        try:
            iFirstWaitForStartInterval = self.intervalType.index(
                IntervalType.WaitForStartSignal
            )
        except ValueError:
            return None

        intervalDurations = self.get_interval_durations()
        return sum(intervalDurations[iFirstWaitForStartInterval + 1 :])

    def get_interval_durations(self) -> list[float]:
        """Returns the durations of the intervals in milliseconds.
        Virtual trigger lines 0-19 are the intervals; a transition time < 0 means "did not occur"
        (interval 0 starts at t = 0)."""
        return [
            t2 - t1
            for t1, t2 in zip(
                self.tPositiveTriggerTransitionMS[:nIntervals],
                self.tNegativeTriggerTransitionMS[:nIntervals],
            )
            if t1 >= 0.0 and t2 > 0.0
        ]


@dataclass
class TdrFile:
    filename: pathlib.Path
    headers: list[Header]

    def get_trials(self) -> list[Trial]:
        trials: list[Trial] = []
        start = next((h for h in self.headers if isinstance(h, FileStartHeader)), None)
        for header in self.headers:
            if isinstance(header, TrialHeader):
                trial = Trial()
                trial.from_trial_header(header)
                if start is not None and trial.tAbsTrialStart:
                    t = datetime.datetime.strptime(trial.tAbsTrialStart, "%H:%M:%S").time()
                    secs = lambda x: x.hour * 3600 + x.minute * 60 + x.second
                    trial.tClockStartS = (secs(t) - secs(start.startTime)) % 86400
                trials.append(trial)
            if isinstance(header, ObjectHeader):
                trials[-1].stimulusObjects.append(header)

        return trials

    def get_trials_with_outcome(self, outcomes: list[TrialOutcome]) -> list[Trial]:
        return [trial for trial in self.get_trials() if trial.outcome in outcomes]

    def get_hits(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.Hit])

    def get_wrongresponses(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.WrongResponse])

    def get_earlyhits(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.EarlyHit])

    def get_earlywrongresponses(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.EarlyWrongResponse])

    def get_earlies(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.Early])

    def get_lates(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.Late])

    def get_eyeerr(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.EyeErr])

    def get_inexpectedstartsignal(self) -> list[Trial]:
        return self.get_trials_with_outcome([TrialOutcome.InexpectedStartSignal])

    def get_wrongstartsignal(self) -> list[TrialHeader]:
        return self.get_trials_with_outcome([TrialOutcome.WrongStartSignal])

    def get_outcome_counts(self) -> dict[str, int]:
        return {
            outcome.name: len(self.get_trials_with_outcome([outcome]))
            for outcome in TrialOutcome
        }

    def get_trials_as_dataframe(self):
        import pandas as pd

        df = pd.DataFrame([vars(trial) for trial in self.get_trials()])
        df.tRelTrialStartMIN = pd.to_timedelta(df.tRelTrialStartMIN, unit="min")
        df.set_index("tRelTrialStartMIN", inplace=True)

        # change dtype of outcome column to categorical
        df["outcome"] = df["outcome"].astype("category")

        # add column with trial duration
        df["trialDurationMS"] = [
            trial.get_trial_duration() for trial in self.get_trials()
        ]

        return df


def read_tdr(filename: pathlib.Path) -> TdrFile:
    # old files contain non-UTF-8 characters (Windows-1252 user/ini names)
    with open(filename, "r", encoding="latin-1") as file:
        lines: list[str] = file.readlines()

    headers: list[Header] = []
    for iLine, line in enumerate(lines):
        # only handle start of headers
        if not line.startswith("$"):
            continue

        if not line.startswith("$FH3"):
            line = remove_comment(line)

        headerId, nLines, headerVersion = line.split()[:3]
        nLines = int(nLines)

        header_enum = HeaderId(headerId)

        # workaround for VStim bug #210: reported nLines is in fact 5, not 4 as reported
        if headerId == HeaderId.TH1.value and int(headerVersion) == 5:
            nLines = 5

        # subheaders are handled within header objects
        if headerId in SubHeaderIdMap.keys():
            continue

        if header_enum == HeaderId.UNKNOWN:
            warnings.warn(f"Unknown header {headerId}", category=UserWarning)
            continue

        if header_enum in HeaderIdMap.keys():
            header = HeaderIdMap[header_enum].from_lines(lines[iLine : iLine + nLines])
            headers.append(header)

    return TdrFile(
        headers=headers,
        filename=filename,
    )
