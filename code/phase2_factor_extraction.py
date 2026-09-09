"""
Phase 2: canonical factor extraction.

Applies the clinician-refined 10-domain / 55-factor taxonomy (see
schema/domain_taxonomy.md) to every note, producing note-level factor
labels, then aggregates to patient level and draws the validation sample.

Run once per model by setting MODEL in your .env file (see .env.example),
e.g. once with your GPT-4o deployment name and once with your GPT-5
deployment name. Output filenames include the model name automatically.

Expects an input CSV with columns: id, description, assessment_type
(patient id, note text, and note type respectively). Set DATA_DIR to the
folder containing that file.
"""
import os
import re
import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from openai import AzureOpenAI
from dotenv import load_dotenv

# -----------------------------
# Setup & config
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
OUTDIR = Path(os.environ.get("OUTPUT_DIR", "./output"))
NOTES_FILE = DATA_DIR / "Patient_notes.csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

client = AzureOpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    api_version=os.environ["API_VERSION"],
    azure_endpoint=os.environ["OPENAI_API_BASE"],
    organization=os.environ.get("OPENAI_ORGANIZATION"),
)
MODEL = os.environ["MODEL"]

OUT_CSV = OUTDIR / f"themes_note_level_{MODEL}.csv"
OUT_CSV2 = OUTDIR / f"themes_patient_level_{MODEL}.csv"
VALIDATION_OUTPUT = OUTDIR / f"validation_sample_{MODEL}.csv"

# -----------------------------
# Load data
# -----------------------------
df = pd.read_csv(NOTES_FILE)
df = df.rename(columns={"id": "patient_id", "description": "note_text"})
df["note_id"] = df.groupby("patient_id").cumcount() + 1
df = df[["patient_id", "note_id", "note_text", "assessment_type"]]

print("Notes:", df.shape, "| unique patients:", df["patient_id"].nunique())

# -----------------------------
# CANONICAL FACTORS
# -----------------------------
CANONICAL_FACTORS = [
    # Alcohol use and relapse risk
    "aud_severity_mild", "aud_severity_moderate", "aud_severity_severe",
    "relapse_risk", "rehab_attempts", "abstinence_under_180_days",
    "abstinence_over_6_months", "cravings", "triggers",

    # Social support and caregiver readiness
    "family_support", "caregiver_availability",
    "caregiver_understanding_and_preparedness", "living_arrangement_stability",

    # Polysubstance and other substance usage
    "tobacco_use", "cannabis_use", "opioids_use", "cocaine_use",
    "benzodiazepine_use", "stimulant_use", "polysubstance_use_history",
    "prescription_misuse",

    # Psychiatric stability and mental health
    "major_depressive_disorder", "anxiety_disorder", "ptsd", "adhd",
    "clinically_significant_insomnia", "suicidal_ideation_behavior",
    "psychiatric_hospitalization_history", "therapy_counseling_engagement",

    # Treatment adherence and transplant motivation
    "motivation_for_transplant", "appointment_medication_adherence",
    "health_literacy", "engagement_in_transplant_education",
    "illness_awareness_treatment_insight",

    # Cognitive and functional status
    "encephalopathy", "delirium", "cognitive_functional_capacity",
    "adl_independence",

    # Financial and socioeconomic stability
    "employment_status", "income_financial_capacity", "insurance_literacy",
    "financial_stressors", "physical_disability_status", "housing_stability",
    "transportation_access",

    # Psychosocial environment and life stressors
    "social_isolation", "family_conflict", "occupational_stress",
    "psychological_trauma_history", "maladaptive_coping_behaviors",

    # Spirituality and coping
    "religious_identity", "faith_based_coping", "meaning_making_presence",
    "value_based_motivation",

    # Safety and legal context
    "abuse_violence_risk", "legal_issues", "safety_planning_commitment",
    "firearms_access_home",
]

# risk = presence (1) is clinically adverse
# protective = presence (1) is clinically beneficial
# neutral = descriptive / mixed / depends on context
FACTOR_POLARITY = {
    "aud_severity_mild": "risk", "aud_severity_moderate": "risk",
    "aud_severity_severe": "risk", "relapse_risk": "risk",
    "rehab_attempts": "risk", "abstinence_under_180_days": "risk",
    "abstinence_over_6_months": "protective", "cravings": "risk",
    "triggers": "risk",

    "family_support": "protective", "caregiver_availability": "protective",
    "caregiver_understanding_and_preparedness": "protective",
    "living_arrangement_stability": "protective",

    "tobacco_use": "risk", "cannabis_use": "risk", "opioids_use": "risk",
    "cocaine_use": "risk", "benzodiazepine_use": "risk",
    "stimulant_use": "risk", "polysubstance_use_history": "risk",
    "prescription_misuse": "risk",

    "major_depressive_disorder": "risk", "anxiety_disorder": "risk",
    "ptsd": "risk", "adhd": "risk",
    "clinically_significant_insomnia": "risk",
    "suicidal_ideation_behavior": "risk",
    "psychiatric_hospitalization_history": "risk",
    "therapy_counseling_engagement": "protective",

    "motivation_for_transplant": "protective",
    "appointment_medication_adherence": "protective",
    "health_literacy": "protective",
    "engagement_in_transplant_education": "protective",
    "illness_awareness_treatment_insight": "protective",

    "encephalopathy": "risk", "delirium": "risk",
    "cognitive_functional_capacity": "protective",
    "adl_independence": "protective",

    "employment_status": "neutral", "income_financial_capacity": "neutral",
    "insurance_literacy": "neutral", "financial_stressors": "risk",
    "physical_disability_status": "risk", "housing_stability": "neutral",
    "transportation_access": "neutral",

    "social_isolation": "risk", "family_conflict": "risk",
    "occupational_stress": "risk", "psychological_trauma_history": "risk",
    "maladaptive_coping_behaviors": "risk",

    "religious_identity": "neutral", "faith_based_coping": "protective",
    "meaning_making_presence": "protective",
    "value_based_motivation": "protective",

    "abuse_violence_risk": "risk", "legal_issues": "risk",
    "safety_planning_commitment": "protective",
    "firearms_access_home": "risk",
}

MUTEX_GROUPS = [
    ["aud_severity_mild", "aud_severity_moderate", "aud_severity_severe"],
    ["abstinence_under_180_days", "abstinence_over_6_months"],
]

DOMAIN_MAP = {
    "alcohol_use_relapse_risk": [
        "aud_severity_mild", "aud_severity_moderate", "aud_severity_severe",
        "relapse_risk", "rehab_attempts", "abstinence_under_180_days",
        "abstinence_over_6_months", "cravings", "triggers",
    ],
    "social_support_caregiver_readiness": [
        "family_support", "caregiver_availability",
        "caregiver_understanding_and_preparedness", "living_arrangement_stability",
    ],
    "polysubstance_usage": [
        "tobacco_use", "cannabis_use", "opioids_use", "cocaine_use",
        "benzodiazepine_use", "stimulant_use", "polysubstance_use_history",
        "prescription_misuse",
    ],
    "psychiatric_stability": [
        "major_depressive_disorder", "anxiety_disorder", "ptsd", "adhd",
        "clinically_significant_insomnia", "suicidal_ideation_behavior",
        "psychiatric_hospitalization_history", "therapy_counseling_engagement",
    ],
    "treatment_adherence_motivation": [
        "motivation_for_transplant", "appointment_medication_adherence",
        "health_literacy", "engagement_in_transplant_education",
        "illness_awareness_treatment_insight",
    ],
    "cognitive_functional_status": [
        "encephalopathy", "delirium", "cognitive_functional_capacity",
        "adl_independence",
    ],
    "financial_socioeconomic": [
        "employment_status", "income_financial_capacity", "insurance_literacy",
        "financial_stressors", "physical_disability_status", "housing_stability",
        "transportation_access",
    ],
    "psychosocial_environment": [
        "social_isolation", "family_conflict", "occupational_stress",
        "psychological_trauma_history", "maladaptive_coping_behaviors",
    ],
    "spirituality_coping": [
        "religious_identity", "faith_based_coping", "meaning_making_presence",
        "value_based_motivation",
    ],
    "safety_legal": [
        "abuse_violence_risk", "legal_issues", "safety_planning_commitment",
        "firearms_access_home",
    ],
}

# -----------------------------
# Prompt
# -----------------------------
SYSTEM_PROMPT = (REPO_ROOT / "prompts" / "phase2_extraction_system_prompt.txt").read_text()


def build_user_prompt(note_text: str) -> str:
    canonical = "\n".join(f"- {t}" for t in CANONICAL_FACTORS)
    return f"""Canonical factors (use these keys exactly):
{canonical}

Note (de-identified):
<<<
{note_text}
>>>

Return ONLY the JSON object, no prose.
"""


# -----------------------------
# Azure OpenAI call
# -----------------------------
def _safe_json_loads(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        s_fix = s.strip()
        s_fix = re.sub(r"```json|```", "", s_fix)
        s_fix = re.sub(r"\s+$", "", s_fix)
        return json.loads(s_fix)


def call_llm_extract(note_text: str, max_retries: int = 3, sleep: float = 1.5) -> Dict[str, Any]:
    """Call LLM to extract factors; return parsed dict or a default all-zeros structure."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(note_text)},
                ],
            )
            content = resp.choices[0].message.content
            parsed = _safe_json_loads(content)

            out = {
                "factor_labels": {k: 0 for k in CANONICAL_FACTORS},
                "factor_documentation": {k: "undocumented" for k in CANONICAL_FACTORS},
                "evidence": {},
                "confidence": {},
            }

            if "factor_labels" in parsed and isinstance(parsed["factor_labels"], dict):
                for k, v in parsed["factor_labels"].items():
                    if k in out["factor_labels"]:
                        out["factor_labels"][k] = int(v) if isinstance(v, (int, bool)) or str(v).isdigit() else 0

            allowed_docs = {"present", "explicitly_denied", "undocumented"}
            if "factor_documentation" in parsed and isinstance(parsed["factor_documentation"], dict):
                for k, v in parsed["factor_documentation"].items():
                    if k in out["factor_documentation"]:
                        val = str(v).strip().lower()
                        if val in allowed_docs:
                            out["factor_documentation"][k] = val

            if "evidence" in parsed and isinstance(parsed["evidence"], dict):
                for k, v in parsed["evidence"].items():
                    if k in CANONICAL_FACTORS and v:
                        out["evidence"][k] = str(v)

            if "confidence" in parsed and isinstance(parsed["confidence"], dict):
                def _clip(x):
                    try:
                        return max(0.0, min(1.0, float(x)))
                    except Exception:
                        return 0.0
                for k, v in parsed["confidence"].items():
                    if k in CANONICAL_FACTORS:
                        out["confidence"][k] = _clip(v)

            for fname in CANONICAL_FACTORS:
                if fname not in out["confidence"]:
                    if (out["factor_documentation"].get(fname) == "undocumented" and
                            out["factor_labels"].get(fname, 0) == 0 and
                            fname not in out["evidence"]):
                        out["confidence"][fname] = 0.2
                    else:
                        out["confidence"][fname] = 0.5

            for group in MUTEX_GROUPS:
                on_flags = [(k, out["factor_labels"].get(k, 0), out["confidence"].get(k, 0.0)) for k in group]
                if sum(v for _, v, _ in on_flags) > 1:
                    keep = sorted([x for x in on_flags if x[1] == 1], key=lambda t: t[2], reverse=True)[0][0]
                    for k, v, _conf in on_flags:
                        if k == keep:
                            out["factor_labels"][k] = 1
                            if out["factor_documentation"].get(k) != "present":
                                out["factor_documentation"][k] = "present"
                        else:
                            out["factor_labels"][k] = 0

            return out

        except Exception:
            if attempt == max_retries:
                traceback.print_exc()
                return {
                    "factor_labels": {k: 0 for k in CANONICAL_FACTORS},
                    "factor_documentation": {k: "undocumented" for k in CANONICAL_FACTORS},
                    "evidence": {},
                    "confidence": {k: 0.0 for k in CANONICAL_FACTORS},
                }
            time.sleep(sleep * attempt)


# -----------------------------
# Run extraction over notes_df
# -----------------------------
def extract_over_df(df_notes: pd.DataFrame, text_col: str = "note_text") -> pd.DataFrame:
    recs: List[Dict[str, Any]] = []
    for i, row in df_notes.iterrows():
        labels = call_llm_extract(str(row[text_col]) or "")
        factors = labels["factor_labels"]
        ev = labels.get("evidence", {})
        conf = labels.get("confidence", {})
        doc = labels.get("factor_documentation", {})

        for fname in CANONICAL_FACTORS:
            recs.append({
                "patient_id": row["patient_id"],
                "note_id": row["note_id"],
                "factor": fname,
                "present": int(factors.get(fname, 0)),
                "documentation": doc.get(fname, "undocumented"),
                "evidence": ev.get(fname, None),
                "confidence": conf.get(fname, None),
            })
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(df_notes)} notes...")
    return pd.DataFrame(recs)


if __name__ == "__main__":
    factors_long = extract_over_df(df, text_col="note_text")
    print("factors_long shape:", factors_long.shape)

    assessment_mapping = df[["patient_id", "note_id", "assessment_type"]].drop_duplicates()
    factors_long = factors_long.merge(assessment_mapping, on=["patient_id", "note_id"], how="left")
    factors_long["polarity"] = factors_long["factor"].map(FACTOR_POLARITY)

    factors_long.to_csv(OUT_CSV, index=False)
    print("Saved:", OUT_CSV)

    # -----------------------------
    # Patient-level aggregation
    # -----------------------------
    any_factor = (
        factors_long.groupby(["patient_id", "factor"])["present"]
        .max()
        .unstack(fill_value=0)
        .reset_index()
    )

    def build_domain_aggregates(row: pd.Series) -> Dict[str, Any]:
        agg = {}
        for dom, feats in DOMAIN_MAP.items():
            vals = [row.get(f, 0) for f in feats]
            agg[f"dom_{dom}_any"] = int(any(vals))
            agg[f"dom_{dom}_intensity"] = int(sum(vals))
        return agg

    domain_agg = any_factor.copy()
    dom_feats = domain_agg.apply(build_domain_aggregates, axis=1, result_type="expand")
    patient_level = pd.concat([domain_agg[["patient_id"]], dom_feats], axis=1)
    patient_level.to_csv(OUT_CSV2, index=False)
    print("Saved:", OUT_CSV2)

    # -----------------------------
    # Validation sample (balanced by assessment type, then by patient)
    # -----------------------------
    print("\nCreating BALANCED validation sample by assessment type...")
    assessment_types = factors_long["assessment_type"].value_counts()

    n_total_validation = 300
    n_per_type = n_total_validation // len(assessment_types)

    validation_sample = []
    for assessment_type in assessment_types.index:
        type_data = factors_long[factors_long["assessment_type"] == assessment_type]

        if len(type_data) >= n_per_type:
            sampled_patients = type_data["patient_id"].unique()
            n_patients_to_sample = min(10, len(sampled_patients))
            selected_patients = np.random.choice(sampled_patients, size=n_patients_to_sample, replace=False)
            type_sample = pd.DataFrame()

            for patient_id in selected_patients:
                patient_data = type_data[type_data["patient_id"] == patient_id]
                n_factors = min(3, len(patient_data))
                patient_sample = patient_data.sample(n=n_factors, random_state=42)
                type_sample = pd.concat([type_sample, patient_sample])
                if len(type_sample) >= n_per_type:
                    break

            if len(type_sample) < n_per_type:
                remaining = n_per_type - len(type_sample)
                additional_sample = type_data[~type_data.index.isin(type_sample.index)].sample(
                    n=remaining, random_state=42
                )
                type_sample = pd.concat([type_sample, additional_sample])
        else:
            type_sample = type_data

        validation_sample.append(type_sample)

    validation_df = pd.concat(validation_sample, ignore_index=True)

    if len(validation_df) > n_total_validation:
        excess = len(validation_df) - n_total_validation
        type_counts = validation_df["assessment_type"].value_counts()
        remove_per_type = max(1, excess // len(type_counts))
        trimmed_samples = []
        for assessment_type in type_counts.index:
            type_data = validation_df[validation_df["assessment_type"] == assessment_type]
            if len(type_data) > remove_per_type:
                type_data = type_data.iloc[:-remove_per_type]
            trimmed_samples.append(type_data)
        validation_df = pd.concat(trimmed_samples, ignore_index=True)

    validation_df = validation_df[[
        "patient_id", "note_id", "assessment_type", "factor", "polarity",
        "present", "documentation", "evidence", "confidence",
    ]]
    validation_df["human_label"] = ""
    validation_df["human_notes"] = ""

    validation_df.to_csv(VALIDATION_OUTPUT, index=False)
    print("Saved balanced validation sample:", VALIDATION_OUTPUT)
    print("\nFinal validation columns:", validation_df.columns.tolist())
