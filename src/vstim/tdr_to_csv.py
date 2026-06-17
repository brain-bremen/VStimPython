"""Convert a TDR file to CSV with trial index, outcome, and reaction time."""

import argparse
import csv
import pathlib
import sys

import vstim.tdr as tdr


def convert(tdr_path: pathlib.Path, csv_path: pathlib.Path) -> None:
    tdr_file = tdr.read_tdr(tdr_path)
    trials = tdr_file.get_trials()

    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trialno", "trialtype", "outcome", "outcome_int", "reactionTimeMS", "trialStartS", "trialEndS"])
        for trial in trials:
            start_s = trial.tRelTrialStartMIN * 60.0
            end_s = start_s + trial.get_trial_duration() / 1000.0
            writer.writerow([
                trial.trialNumber,
                trial.stimulusNumber,
                trial.outcome.name,
                trial.outcome.value,
                trial.reactionTimeMS,
                round(start_s, 6),
                round(end_s, 6),
            ])

    print(f"Wrote {len(trials)} trials to {csv_path}")


def _pick_tdr_file() -> pathlib.Path | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select TDR file",
        filetypes=[("TDR files", "*.tdr"), ("All files", "*.*")],
    )
    root.destroy()
    return pathlib.Path(path) if path else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert TDR to CSV.")
    parser.add_argument("tdr_file", type=pathlib.Path, nargs="?", help="Input .tdr file")
    parser.add_argument(
        "csv_file",
        type=pathlib.Path,
        nargs="?",
        help="Output .csv file (default: same name as input with .csv extension)",
    )
    args = parser.parse_args()

    tdr_path = args.tdr_file
    if tdr_path is None:
        tdr_path = _pick_tdr_file()
        if tdr_path is None:
            print("No file selected.", file=sys.stderr)
            sys.exit(1)

    if not tdr_path.exists():
        print(f"Error: {tdr_path} not found", file=sys.stderr)
        sys.exit(1)

    csv_path = args.csv_file or tdr_path.with_suffix(".csv")
    convert(tdr_path, csv_path)


if __name__ == "__main__":
    main()
