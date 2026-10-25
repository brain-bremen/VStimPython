"""Reader for VStim stimulus definition files (.ini, file version 5; VStim 1.1, 2001-2004).

Only .ini file version 5 is supported. The layout changes from version to version, in
particular with VStim 2.0 (program version in the file header, JSON blocks), so :func:`read`
rejects other versions right away (:class:`UnsupportedIniVersion`).

The file is VStim's archive: one value per line, right-aligned, followed by `/* comment`. Read here:
  - stimulus table: presentations per round and time sequence for each stimulus number
  - time sequences: per interval the duration (FixTime, ms), random extension (RandItv, MaxNoRandtvs) and flags
  - eye windows
  - object queue: per object the type, queue number, visibility, position (x, y, z mm) and rotation, the type-specific
    values as (comment, value) pairs; for "Fixation Point 1" (CObjFixPoint1, VStim ObjFixPoint1.cpp) the member squares:
    used, on/off trigger (virtual trigger line: positive flank shows, negative flank hides), stimuli on which shown,
    size, colour. Members are drawn at the parent object's position (SetUserDefinedTransformMmRad of the parent).

Not decoded: other object types beyond their header and (comment, value) pairs.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

_LINE = re.compile(r"^\s*(?P<val>.*?)\s*/\*\s*(?P<com>.*?)\s*$")
SUPPORTED_FILE_VERSIONS = (5,)


class UnsupportedIniVersion(ValueError):
    """The .ini file has a layout this reader does not know."""


def check_version(path) -> int:
    """.ini file version of ``path``; raises :class:`UnsupportedIniVersion` unless it is supported."""
    with open(path, "rb") as file:
        head = [file.readline().decode("latin-1") for _ in range(3)]
    values = {}
    for line in head:
        m = _LINE.match(line.rstrip("\r\n"))
        if m:
            values.setdefault(m["com"].split(";")[0].strip(), m["val"])  # the first VERSION is the file version
    try:
        version = int(values["VERSION"])
    except (KeyError, ValueError):
        raise UnsupportedIniVersion(f"{path}: no .ini file version in the first line") from None
    if "PROG VERS MAJOR" in values and int(values["PROG VERS MAJOR"]) >= 2:
        raise UnsupportedIniVersion(
            f"{path}: written by VStim {values['PROG VERS MAJOR']}.{values.get('PROG VERS MINOR', '?')} "
            f"(.ini file version {version}); only VStim 1.x .ini files (version 5) are supported"
        )
    if version not in SUPPORTED_FILE_VERSIONS:
        raise UnsupportedIniVersion(f"{path}: .ini file version {version}; only version 5 is supported")
    return version


@dataclasses.dataclass
class Interval:
    duration_ms: float
    rand_ms: float
    max_rand_steps: int
    go_next_on_subject_start: int
    break_on_eye_error: int
    response_required: int
    response_allowed: int
    start_src: int
    resp_src: int


@dataclasses.dataclass
class TimeSequence:
    intervals: list[Interval]
    check_eye: int
    recording_trigger_interval: int


@dataclasses.dataclass
class Member:
    used: bool
    on_trigger: int
    off_trigger: int
    stimuli: set[int]
    width_mm: float | None = None
    height_mm: float | None = None
    form: int | None = None
    rgb: tuple[int, int, int] | None = None
    user_visible: int | None = None


@dataclasses.dataclass
class Object:
    type: str
    queue_number: int
    user_visible: int
    system_visible: int
    x_mm: float
    y_mm: float
    z_mm: float
    rot_rad: tuple[float, float, float]
    values: list[tuple[str, str]]          # type-specific (comment, value) pairs after the header
    members: list[Member] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class StimIni:
    path: str
    n_stimuli: int
    presentations: dict[int, tuple[int, int]]   # stimulus -> (presentations per round, time sequence)
    flags: dict[str, int]
    time_sequences: list[TimeSequence]
    eye_windows: list[tuple[float, float, float, float, int]]
    objects: list[Object]

    def stimuli_used(self):
        return sorted(s for s, (n, _) in self.presentations.items() if n > 0)


def parse_stim_list(s):
    """'1, 2, 5:7,' -> {1, 2, 5, 6, 7} (VStim StimNoList)."""
    out = set()
    for part in s.replace(" ", "").split(","):
        if not part:
            continue
        if ":" in part:
            a, b = part.split(":")[:2]
            out.update(range(int(a), int(b) + 1))
        elif re.fullmatch(r"-?\d+", part):
            out.add(int(part))
    return out


def _lines(path):
    raw = Path(path).read_bytes().decode("latin-1").replace("\r", "").split("\n")
    out = []
    for ln in raw:
        if not ln.strip():
            continue
        m = _LINE.match(ln)
        out.append((m["val"], m["com"]) if m else (ln.strip(), ""))
    return out


def read(path) -> StimIni:
    check_version(path)
    L = _lines(path)
    i = 0

    def nxt():
        nonlocal i
        v = L[i]
        i += 1
        return v

    def find(text):
        nonlocal i
        while i < len(L) and L[i][0] != text and not L[i][1].startswith(text) and L[i][0].strip() != text:
            i += 1
        if i >= len(L):
            raise ValueError(f"{path}: '{text}' not found")

    find("STIMULUS DEFINITION MODULE DESCRIPTION")
    nxt()
    nxt()  # version
    n_stim = int(nxt()[0])
    flags = {}
    while not L[i][1].startswith("Stimulus"):
        v, c = nxt()
        flags[c] = int(float(v))
    pres = {}
    while i < len(L) and L[i][1].startswith("Stimulus"):
        v, c = nxt()
        k = int(re.match(r"Stimulus\s+(\d+)", c)[1])
        a, b = v.split()[:2]
        pres[k] = (int(a), int(b))

    find("EXPERIMENTAL CONTROL UNIT DEFINITION")
    nxt()
    nxt()  # version
    n_seq = int(nxt()[0])
    seqs = []
    for _ in range(n_seq):
        nxt()  # version
        n_itv = int(nxt()[0])
        if L[i][0] == "" and L[i][1].startswith("Version"):
            nxt()  # column header
        itvs = []
        for _ in range(n_itv):
            v, _c = nxt()
            p = v.split()
            itvs.append(Interval(float(p[1]), float(p[2]), int(p[3]), *[int(x) for x in p[4:10]]))
        check_eye = int(nxt()[0])
        nxt()  # simulate
        rec = int(nxt()[0])
        seqs.append(TimeSequence(itvs, check_eye, rec))

    find("EYE MONITOR DEFINITION")
    eye = []
    while i < len(L) and L[i][0] != "COMMON RESOURCE DEFINITION":
        v, c = nxt()
        if c.startswith("Window"):
            p = v.split()
            eye.append((float(p[0]), float(p[1]), float(p[2]), float(p[3]), int(p[4])))

    objs = []
    find("OBJECT LIST START")
    while i < len(L):
        if L[i][0] != "OBJECT":
            i += 1
            continue
        nxt()
        objs.append(_read_object(L, i, path))
        i = objs[-1]._end
    for o in objs:
        del o._end
    return StimIni(str(path), n_stim, pres, flags, seqs, eye, objs)


def _header(L, i):
    """CObj header from the type-name line; returns (type, queue, uvis, svis, xyz, rot, next index)."""
    typ = L[i][0]
    i += 2  # type name, CObj version
    q = int(L[i][0]); uv = int(L[i + 1][0]); sv = int(L[i + 2][0])
    xyz = [float(L[i + 3 + k][0]) for k in range(3)]
    rot = tuple(float(L[i + 6 + k][0]) for k in range(3))
    return typ, q, uv, sv, xyz, rot, i + 9


def _read_object(L, i, path):
    typ, q, uv, sv, xyz, rot, i = _header(L, i)
    obj = Object(typ, q, uv, sv, *xyz, rot, [])
    if typ == "Fixation Point 1":
        i += 1  # VERSION (ObjFixPoint1)
        obj.values.append(("Trigger causing disappearance of objects", L[i][0])); i += 1
        n = int(L[i][0]); i += 1
        for _ in range(n):
            used = L[i][1].startswith("Member object used")
            on, off = int(L[i + 1][0]), int(L[i + 2][0])
            stims = parse_stim_list(L[i + 3][0])
            i += 4
            mtyp, _q, muv, _sv, _xyz, _rot, i = _header(L, i)
            m = Member(used, on, off, stims, user_visible=muv)
            rgb = []
            while i < len(L) and not (L[i][1].startswith("Member object") or L[i][0] == "OBJECT"):
                v, c = L[i]
                if c.startswith("width of rectangle") or c.startswith("diameter"):
                    m.width_mm = float(v)
                elif c.startswith("height of rectangle"):
                    m.height_mm = float(v)
                elif c.startswith("Form:"):
                    m.form = int(v)
                elif re.match(r"(red|green|blue) component of fill color", c):
                    rgb.append(int(float(v)))
                i += 1
            if len(rgb) == 3:
                m.rgb = tuple(rgb)
            obj.members.append(m)
    else:
        while i < len(L) and L[i][0] != "OBJECT":
            obj.values.append((L[i][1], L[i][0]))
            i += 1
    obj._end = i
    return obj
