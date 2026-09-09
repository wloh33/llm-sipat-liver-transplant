"""
Table 1 note descriptives: note counts and note length by assessment type.

Produces the note-count / note-length rows of Table 1. Does not touch or
output patient demographics (age, sex, race, BMI, SIPAT) -- those are
computed separately.

Expects an input CSV with columns: id, description, assessment_type
(patient id, note text, and note type respectively). Set DATA_DIR to the
folder containing that file.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
OUTDIR = Path(os.environ.get("OUTPUT_DIR", "./output"))
NOTES_FILE = DATA_DIR / "Patient_notes.csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(NOTES_FILE)

df["note_text_clean"] = (
    df["description"]
    .fillna("")
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

total_notes = len(df)
total_patients = df["id"].nunique()
df["note_length_words"] = df["note_text_clean"].str.split().apply(len)

table1 = (
    df.groupby("assessment_type")
    .agg(
        n_notes=("note_text_clean", "count"),
        n_patients=("id", "nunique"),
        mean_note_length_words=("note_length_words", "mean"),
        median_note_length_words=("note_length_words", "median"),
    )
    .reset_index()
)

table1["notes_percent_of_total"] = 100 * table1["n_notes"] / total_notes
table1["patients_percent_with_type"] = 100 * table1["n_patients"] / total_patients

for c in ["mean_note_length_words", "median_note_length_words",
          "notes_percent_of_total", "patients_percent_with_type"]:
    table1[c] = table1[c].round(1)

total_row = pd.DataFrame({
    "assessment_type": ["Total"],
    "n_notes": [total_notes],
    "n_patients": [total_patients],
    "mean_note_length_words": [np.nan],
    "median_note_length_words": [np.nan],
    "notes_percent_of_total": [100.0],
    "patients_percent_with_type": [100.0],
})
table1 = pd.concat([table1, total_row], ignore_index=True)

out_xlsx = OUTDIR / "table1_note_descriptives.xlsx"
table1.to_excel(out_xlsx, index=False)
print("Wrote:", out_xlsx)
