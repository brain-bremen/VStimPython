# Python tools for VStim

[![Python Tests](https://github.com/brain-bremen/vstim-python-tools/actions/workflows/python-tests.yml/badge.svg)](https://github.com/brain-bremen/vstim-python-tools/actions/workflows/python-tests.yml)

This repository contains Python tools for analyzing output files (currently TDR only) of the
visual stimulation software VStim used at the Brain Research Institute of University of
Bremen.

In future versions, tools for remote controlling/scripting VStim, manipulating the config
files and event files may be added.

## Tools

### tdr-to-csv

Converts a TDR file to CSV with one row per trial, including trial index, trial type,
outcome, reaction time, and trial start/end times.

**Install and run with uv (no manual install needed):**

```bash
uvx --from "git+https://github.com/brain-bremen/VStimPython" tdr-to-csv path/to/file.tdr
```

This writes `path/to/file.csv` next to the input file. To specify the output path explicitly:

```bash
uvx --from "git+https://github.com/brain-bremen/VStimPython" tdr-to-csv path/to/file.tdr path/to/output.csv
```

**If the package is already installed:**

```bash
tdr-to-csv path/to/file.tdr
```