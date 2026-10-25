# Changelog

## [0.3.0] - 2026-10-25

- **Added** reading of TDR files of old VStim versions (1.2-1.8, file format < 1.05): `$FH1` v1/v2,
  `$TH1` layouts detected from the number of tokens (the version is always 1 before VStim 1.40),
  `$TS1` v1/v2, optional `$TS2`-`$TS4`, `$FH2` (end counts) and `$FH3` (JSON session metadata);
  files are read as latin-1. `Trial.tClockStartS` gives the trial start from the wall clock.
- **Added** trial outcomes `Undetermined` (-1) and `Cancelled` (10) (VStim `TDR.h`); unknown outcome
  codes are kept (`TrialOutcome(42).name == "Unknown42"`) with a warning instead of failing.
- **Added** `vstim.ini`: reader for VStim 1.x stimulus definition files (.ini file version 5):
  stimulus table, time sequences, eye windows and object queue (with Fixation Point 1 members).
  Other versions, in particular files of VStim 2.0 and newer, are rejected with
  `UnsupportedIniVersion`.
- **Changed** `get_interval_durations` includes interval 0.

## [0.2.0] - 2026-06-17

- **Added** `tdr-to-csv` command-line tool: converts a TDR file to CSV with columns for trial
  index, trial type, outcome, reaction time, and trial start/end times.

## [0.1.0]

- Initial release with TDR file parsing (`vstim.tdr`).
